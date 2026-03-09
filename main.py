# galatiq-invoices/main.py
import sys
from pathlib import Path
from main import run_cli
import argparse

# add backend to path and run
sys.path.insert(0, str(Path(__file__).parent / "backend"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--invoice_path", required=True)
    args = parser.parse_args()
    run_cli(args.invoice_path)