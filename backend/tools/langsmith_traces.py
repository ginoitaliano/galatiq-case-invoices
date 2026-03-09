#!/usr/bin/env python3
# backend/tools/langsmith_traces.py
"""
LangSmith trace summary — pulls recent traces and shows agent performance.
Useful for demo and debugging: "here's exactly what each agent did."

Usage:
    python tools/langsmith_traces.py
    python tools/langsmith_traces.py --runs 20
    python tools/langsmith_traces.py --invoice INV-1001
    python tools/langsmith_traces.py --errors-only
"""
import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Optional
from langsmith import Client


def get_langsmith_client():
    """Get LangSmith client,fail gracefully if not configured."""
    try:
        api_key = os.getenv("LANGCHAIN_API_KEY")
        if not api_key:
            print("ERROR: LANGCHAIN_API_KEY not set in .env")
            sys.exit(1)
        return Client(api_key=api_key)
    except ImportError:
        print("ERROR: langsmith not installed. Run: pip install langsmith")
        sys.exit(1)


def format_duration(ms: Optional[float]) -> str:
    if ms is None:
        return "N/A"
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms/1000:.1f}s"


def format_tokens(tokens: Optional[int]) -> str:
    if tokens is None:
        return "N/A"
    if tokens > 1000:
        return f"{tokens/1000:.1f}k"
    return str(tokens)


def print_trace_summary(runs: list, verbose: bool = False):
    """Print a formatted summary of LangSmith runs."""

    total = len(runs)
    errors = sum(1 for r in runs if r.error)
    successes = total - errors

    print("\n" + "="*65)
    print("  LANGSMITH TRACE SUMMARY:GALATIQ INVOICE PIPELINE")
    print("="*65)
    print(f"  Project  : {os.getenv('LANGCHAIN_PROJECT', 'galatiq-invoices')}")
    print(f"  Runs     : {total} | Success: {successes} | Errors: {errors}")
    print("="*65)

    for run in runs:
        # status
        icon = "✓" if not run.error else "✗"
        name = run.name or "unnamed"
        total_tokens = format_duration(None)

        # timing
        started = run.start_time.strftime("%H:%M:%S") if run.start_time else "N/A"
        latency = ""
        if run.start_time and run.end_time:
            delta = (run.end_time - run.start_time).total_seconds()
            latency = f"{delta:.1f}s"

        # tokens
        prompt_tokens = format_tokens(run.prompt_tokens)
        completion_tokens = format_tokens(run.completion_tokens)

        print(f"\n  {icon}  [{started}] {name}")
        print(f"     Latency: {latency} | Tokens: {prompt_tokens} → {completion_tokens}")

        if run.error:
            error_snippet = str(run.error)[:100]
            print(f"     ERROR: {error_snippet}")

        if verbose and run.outputs:
            outputs = str(run.outputs)[:150]
            print(f"     Output: {outputs}")

        # show child runs (agent steps)
        if verbose and hasattr(run, "child_runs") and run.child_runs:
            for child in run.child_runs[:5]:
                child_icon = "✓" if not child.error else "✗"
                child_latency = ""
                if child.start_time and child.end_time:
                    delta = (child.end_time - child.start_time).total_seconds()
                    child_latency = f"{delta:.1f}s"
                print(f"       {child_icon} {child.name} ({child_latency})")


def print_agent_performance(runs: list):
    """Break down performance by agent node."""
    agent_stats: dict = {}

    for run in runs:
        name = run.name or "unknown"
        if name not in agent_stats:
            agent_stats[name] = {"count": 0, "errors": 0, "total_ms": 0}

        agent_stats[name]["count"] += 1
        if run.error:
            agent_stats[name]["errors"] += 1
        if run.start_time and run.end_time:
            ms = (run.end_time - run.start_time).total_seconds() * 1000
            agent_stats[name]["total_ms"] += ms

    if not agent_stats:
        return

    print("\n  AGENT PERFORMANCE BREAKDOWN")
    print("  " + "-"*45)
    print(f"  {'Agent':<20} {'Runs':>5} {'Errors':>7} {'Avg Latency':>12}")
    print("  " + "-"*45)

    for name, stats in sorted(agent_stats.items()):
        avg_ms = stats["total_ms"] / stats["count"] if stats["count"] > 0 else 0
        error_rate = f"{stats['errors']}/{stats['count']}"
        avg_latency = format_duration(avg_ms)
        print(f"  {name:<20} {stats['count']:>5} {error_rate:>7} {avg_latency:>12}")


def main():
    parser = argparse.ArgumentParser(description="LangSmith trace viewer for Galatiq pipeline")
    parser.add_argument("--runs", type=int, default=10, help="Number of recent runs to show")
    parser.add_argument("--invoice", help="Filter by invoice number in run name")
    parser.add_argument("--errors-only", action="store_true", help="Show only failed runs")
    parser.add_argument("--verbose", action="store_true", help="Show run inputs/outputs")
    parser.add_argument("--hours", type=int, default=24, help="Look back N hours")
    parser.add_argument("--perf", action="store_true", help="Show agent performance breakdown")
    args = parser.parse_args()

    client = get_langsmith_client()
    project = os.getenv("LANGCHAIN_PROJECT", "galatiq-invoices")

    print(f"\nFetching traces from LangSmith project: {project}...")

    try:
        # build filter
        filters = {}
        if args.errors_only:
            filters["error"] = True

        start_time = datetime.now() - timedelta(hours=args.hours)

        runs = list(client.list_runs(
            project_name=project,
            start_time=start_time,
            limit=args.runs,
            **filters
        ))

        if not runs:
            print(f"No runs found in the last {args.hours} hours.")
            print("Make sure LANGCHAIN_TRACING_V2=true in your .env and you've processed at least one invoice.")
            return

        # filter by invoice number if requested
        if args.invoice:
            runs = [r for r in runs if args.invoice.lower() in str(r.name or "").lower()]
            if not runs:
                print(f"No runs found matching invoice: {args.invoice}")
                return

        print_trace_summary(runs, verbose=args.verbose)

        if args.perf:
            print_agent_performance(runs)

        print(f"\n  View full traces at: https://smith.langchain.com/o/your-org/projects/p/{project}\n")

    except Exception as e:
        print(f"\nERROR fetching traces: {str(e)}")
        print("Check that your LANGCHAIN_API_KEY is valid and the project exists.")
        sys.exit(1)


if __name__ == "__main__":
    main()