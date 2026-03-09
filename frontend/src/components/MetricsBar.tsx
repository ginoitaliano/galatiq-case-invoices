import React from "react";
import { Metrics } from "../api/client";

interface Props {
  metrics: Metrics;
}

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

export const MetricsBar: React.FC<Props> = ({ metrics }) => {
  const cards = [
    { label: "Total Invoices", value: metrics.total, sub: null, color: "#e2e8f0" },
    { label: "Approved", value: metrics.approved, sub: `${metrics.approval_rate}%`, color: "#4ade80" },
    { label: "Rejected", value: metrics.rejected, sub: `${metrics.rejection_rate}%`, color: "#f87171" },
    { label: "Pending VP", value: metrics.pending_vp, sub: "awaiting decision", color: "#facc15" },
    { label: "Total Paid", value: fmt(metrics.total_paid), sub: null, color: "#60a5fa" },
    { label: "Avg Invoice", value: fmt(metrics.average_invoice_value), sub: null, color: "#a78bfa" },
  ];

  return (
    <div style={styles.bar}>
      {cards.map((c) => (
        <div key={c.label} style={styles.card}>
          <div style={{ ...styles.dot, background: c.color }} />
          <div>
            <div style={styles.cardLabel}>{c.label}</div>
            <div style={styles.cardValue}>{c.value}</div>
            {c.sub && <div style={styles.cardSub}>{c.sub}</div>}
          </div>
        </div>
      ))}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: "grid",
    gridTemplateColumns: "repeat(6, 1fr)",
    gap: "1px",
    background: "#1a1a1a",
    borderBottom: "1px solid #1a1a1a",
  },
  card: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "20px 24px",
    background: "#0d0d0d",
    transition: "background 0.15s",
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    flexShrink: 0,
  },
  cardLabel: {
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    color: "#555",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 4,
  },
  cardValue: {
    fontSize: 22,
    fontFamily: "'Syne', sans-serif",
    fontWeight: 700,
    color: "#f0f0f0",
    lineHeight: 1,
  },
  cardSub: {
    fontSize: 11,
    color: "#444",
    fontFamily: "'DM Mono', monospace",
    marginTop: 3,
  },
};
