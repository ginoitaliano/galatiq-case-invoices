import React from "react";
import { InvoiceSummary, api } from "../api/client";

interface Props {
  approvals: InvoiceSummary[];
  onDecision: () => void;
}

const fmt = (n: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);

export const VPApprovalPanel: React.FC<Props> = ({ approvals, onDecision }) => {
  const [notes, setNotes] = React.useState<Record<string, string>>({});
  const [loading, setLoading] = React.useState<Record<string, boolean>>({});

  const handleDecision = async (invoiceNumber: string, decision: "approve" | "reject") => {
    setLoading((l) => ({ ...l, [invoiceNumber]: true }));
    await api.submitVPDecision(invoiceNumber, decision, notes[invoiceNumber]);
    setLoading((l) => ({ ...l, [invoiceNumber]: false }));
    onDecision();
  };

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <div style={styles.title}>VP QUEUE</div>
        {approvals.length > 0 && (
          <div style={styles.badge}>{approvals.length}</div>
        )}
      </div>

      {approvals.length === 0 ? (
        <div style={styles.empty}>No pending approvals</div>
      ) : (
        <div style={styles.list}>
          {approvals.map((inv) => (
            <div key={inv.invoice_number} style={styles.card}>
              <div style={styles.cardHeader}>
                <span style={styles.invoiceNum}>{inv.invoice_number}</span>
                <span style={styles.amount}>{fmt(inv.total, inv.currency)}</span>
              </div>
              <div style={styles.vendor}>{inv.vendor}</div>

              <textarea
                style={styles.noteInput}
                placeholder="Add a note (optional)..."
                value={notes[inv.invoice_number] || ""}
                onChange={(e) =>
                  setNotes((n) => ({ ...n, [inv.invoice_number]: e.target.value }))
                }
                rows={2}
              />

              <div style={styles.buttons}>
                <button
                  style={{ ...styles.btn, ...styles.approveBtn }}
                  disabled={loading[inv.invoice_number]}
                  onClick={() => handleDecision(inv.invoice_number, "approve")}
                >
                  {loading[inv.invoice_number] ? "..." : "APPROVE"}
                </button>
                <button
                  style={{ ...styles.btn, ...styles.rejectBtn }}
                  disabled={loading[inv.invoice_number]}
                  onClick={() => handleDecision(inv.invoice_number, "reject")}
                >
                  {loading[inv.invoice_number] ? "..." : "REJECT"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 260,
    borderLeft: "1px solid #1a1a1a",
    background: "#0a0a0a",
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "16px",
    borderBottom: "1px solid #1a1a1a",
  },
  title: {
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    color: "#444",
    letterSpacing: "0.1em",
  },
  badge: {
    background: "#facc1520",
    color: "#facc15",
    border: "1px solid #facc1540",
    borderRadius: 10,
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    padding: "2px 8px",
  },
  empty: {
    padding: 20,
    color: "#2a2a2a",
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    textAlign: "center",
  },
  list: {
    flex: 1,
    overflowY: "auto",
    padding: 12,
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  card: {
    background: "#111",
    border: "1px solid #1e1e1e",
    borderRadius: 6,
    padding: 14,
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  invoiceNum: {
    fontSize: 12,
    fontFamily: "'DM Mono', monospace",
    color: "#ccc",
    fontWeight: 600,
  },
  amount: {
    fontSize: 13,
    fontFamily: "'Syne', sans-serif",
    fontWeight: 700,
    color: "#facc15",
  },
  vendor: {
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    color: "#444",
    marginBottom: 10,
  },
  noteInput: {
    width: "100%",
    background: "#0d0d0d",
    border: "1px solid #1a1a1a",
    borderRadius: 4,
    padding: "7px 9px",
    color: "#888",
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    resize: "none",
    outline: "none",
    boxSizing: "border-box",
    marginBottom: 10,
  },
  buttons: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 6,
  },
  btn: {
    border: "none",
    borderRadius: 4,
    padding: "8px 0",
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    fontWeight: 700,
    letterSpacing: "0.06em",
    cursor: "pointer",
  },
  approveBtn: {
    background: "#0d2b1a",
    color: "#4ade80",
    border: "1px solid #1a4d2e",
  },
  rejectBtn: {
    background: "#2b0d0d",
    color: "#f87171",
    border: "1px solid #4d1a1a",
  },
};
