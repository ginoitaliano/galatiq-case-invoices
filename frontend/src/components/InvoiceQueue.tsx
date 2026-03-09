import React from "react";
import { InvoiceSummary } from "../api/client";

interface Props {
  invoices: InvoiceSummary[];
  selected: string | null;
  onSelect: (id: string) => void;
  onProcess: (path: string) => void;
}

const STAGE_COLORS: Record<string, string> = {
  ingestion: "#60a5fa",
  validation: "#818cf8",
  finance_review: "#a78bfa",
  awaiting_vp: "#facc15",
  complete: "#4ade80",
  rejected: "#f87171",
  failed: "#ef4444",
};

const STAGE_LABELS: Record<string, string> = {
  ingestion: "Ingesting",
  validation: "Validating",
  finance_review: "Finance Review",
  awaiting_vp: "VP Approval",
  complete: "Complete",
  rejected: "Rejected",
  failed: "Failed",
};

const fmtCurrency = (n: number, currency: string) => {
  if (!n && n !== 0) return "$—";
  const code = currency || "USD";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: code, maximumFractionDigits: 0 }).format(n);
};

export const InvoiceQueue: React.FC<Props> = ({ invoices, selected, onSelect, onProcess }) => {
  const [filePath, setFilePath] = React.useState("");
  const [processing, setProcessing] = React.useState(false);

  const handleProcess = async () => {
    if (!filePath.trim()) return;
    setProcessing(true);
    await onProcess(filePath.trim());
    setFilePath("");
    setProcessing(false);
  };

  return (
    <div style={styles.panel}>
      {/* Process new invoice input */}
      <div style={styles.inputSection}>
        <div style={styles.inputLabel}>PROCESS INVOICE</div>
        <input
          style={styles.input}
          placeholder="data/invoices/invoice_1001.txt"
          value={filePath}
          onChange={(e) => setFilePath(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleProcess()}
        />
        <button
          style={{ ...styles.btn, opacity: processing ? 0.5 : 1 }}
          onClick={handleProcess}
          disabled={processing}
        >
          {processing ? "QUEUING..." : "RUN →"}
        </button>
      </div>

      {/* Invoice list */}
      <div style={styles.listHeader}>
        <span>INVOICE QUEUE</span>
        <span style={styles.count}>{invoices.length}</span>
      </div>

      <div style={styles.list}>
        {invoices.length === 0 && (
          <div style={styles.empty}>No invoices processed yet.<br />Submit a file path above to begin.</div>
        )}
        {invoices.map((inv) => {
          const isSelected = selected === inv.invoice_number;
          const stageColor = STAGE_COLORS[inv.current_stage] || "#555";
          return (
            <div
              key={inv.invoice_number}
              style={{
                ...styles.item,
                background: isSelected ? "#1a1a1a" : "transparent",
                borderLeft: isSelected ? `2px solid ${stageColor}` : "2px solid transparent",
              }}
              onClick={() => onSelect(inv.invoice_number)}
            >
              <div style={styles.itemTop}>
                <span style={styles.invoiceNum}>{inv.invoice_number}</span>
                <span style={{ ...styles.stageBadge, color: stageColor }}>
                  {STAGE_LABELS[inv.current_stage] || inv.current_stage}
                </span>
              </div>
              <div style={styles.itemBottom}>
                <span style={styles.vendor}>{inv.vendor}</span>
                <span style={styles.amount}>{fmtCurrency(inv.total, inv.currency)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 300,
    borderRight: "1px solid #1a1a1a",
    display: "flex",
    flexDirection: "column",
    background: "#0a0a0a",
    flexShrink: 0,
  },
  inputSection: {
    padding: "20px 16px",
    borderBottom: "1px solid #1a1a1a",
  },
  inputLabel: {
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    color: "#444",
    letterSpacing: "0.1em",
    marginBottom: 8,
  },
  input: {
    width: "100%",
    background: "#111",
    border: "1px solid #222",
    borderRadius: 4,
    padding: "8px 10px",
    color: "#ccc",
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    marginBottom: 8,
    outline: "none",
    boxSizing: "border-box",
  },
  btn: {
    width: "100%",
    background: "#f0f0f0",
    color: "#000",
    border: "none",
    borderRadius: 4,
    padding: "8px",
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    fontWeight: 700,
    letterSpacing: "0.08em",
    cursor: "pointer",
  },
  listHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 16px",
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    color: "#444",
    letterSpacing: "0.1em",
    borderBottom: "1px solid #1a1a1a",
  },
  count: {
    background: "#1a1a1a",
    color: "#666",
    padding: "2px 7px",
    borderRadius: 10,
    fontSize: 10,
  },
  list: {
    flex: 1,
    overflowY: "auto",
  },
  item: {
    padding: "12px 16px",
    cursor: "pointer",
    borderBottom: "1px solid #111",
    transition: "background 0.1s",
  },
  itemTop: {
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
  stageBadge: {
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  itemBottom: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  vendor: {
    fontSize: 11,
    color: "#555",
    fontFamily: "'DM Mono', monospace",
  },
  amount: {
    fontSize: 12,
    color: "#888",
    fontFamily: "'Syne', sans-serif",
    fontWeight: 600,
  },
  empty: {
    padding: 24,
    color: "#333",
    fontSize: 12,
    fontFamily: "'DM Mono', monospace",
    lineHeight: 1.7,
    textAlign: "center",
  },
};
