import React from "react";
import { InvoiceDetail as IDetail } from "../api/client";

interface Props {
  invoice: IDetail | null;
  loading: boolean;
}

const fmt = (n: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(n);

const Flag: React.FC<{ label: string; active: boolean }> = ({ label, active }) => (
  <span style={{
    display: "inline-block",
    padding: "3px 10px",
    borderRadius: 3,
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    letterSpacing: "0.06em",
    marginRight: 6,
    marginBottom: 6,
    background: active ? "#2d1111" : "#111",
    color: active ? "#f87171" : "#333",
    border: `1px solid ${active ? "#5a1e1e" : "#1a1a1a"}`,
  }}>
    {active ? "✗" : "✓"} {label}
  </span>
);

export const InvoiceDetailPanel: React.FC<Props> = ({ invoice, loading }) => {
  if (loading) return (
    <div style={styles.empty}>
      <div style={styles.spinner} />
      <div style={styles.emptyText}>Loading invoice...</div>
    </div>
  );

  if (!invoice) return (
    <div style={styles.empty}>
      <div style={styles.emptyIcon}>◈</div>
      <div style={styles.emptyText}>Select an invoice to view details</div>
    </div>
  );

  const stageColor: Record<string, string> = {
    awaiting_vp: "#facc15",
    complete: "#4ade80",
    rejected: "#f87171",
    failed: "#ef4444",
  };

  return (
    <div style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <div style={styles.invoiceNum}>{invoice.invoice_number}</div>
          <div style={styles.vendor}>{invoice.vendor}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={styles.amount}>{fmt(invoice.total, invoice.currency)}</div>
          <div style={{
            ...styles.stagePill,
            color: stageColor[invoice.current_stage] || "#888",
            borderColor: stageColor[invoice.current_stage] || "#222",
          }}>
            {invoice.current_stage.replace(/_/g, " ").toUpperCase()}
          </div>
        </div>
      </div>

      <div style={styles.body}>
        {/* Validation Flags */}
        {invoice.validation_flags && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>VALIDATION FLAGS</div>
            <div>
              <Flag label="Fraudulent" active={invoice.validation_flags.is_fraudulent} />
              <Flag label="Out of Stock" active={invoice.validation_flags.is_out_of_stock} />
              <Flag label="Unknown Item" active={invoice.validation_flags.is_unknown_item} />
              <Flag label="Data Integrity" active={invoice.validation_flags.is_data_integrity_issue} />
              <Flag label="Qty Mismatch" active={invoice.validation_flags.is_quantity_mismatch} />
              <Flag label="Total Mismatch" active={invoice.validation_flags.is_total_mismatch} />
            </div>
            {invoice.validation_flags.details.length > 0 && (
              <div style={styles.flagDetails}>
                {invoice.validation_flags.details.map((d: string, i: number) => (
                  <div key={i} style={styles.flagDetail}>→ {d}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Finance Reasoning */}
        {invoice.finance_reasoning && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>
              FINANCE AGENT REASONING
              {invoice.finance_confidence && (
                <span style={styles.confidence}>
                  {Math.round(invoice.finance_confidence * 100)}% confidence
                </span>
              )}
            </div>
            <div style={styles.reasoning}>{invoice.finance_reasoning}</div>
          </div>
        )}

        {/* VP Decision */}
        {invoice.vp_decision && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>VP DECISION</div>
            <div style={{
              ...styles.vpDecision,
              color: invoice.vp_decision === "approve" ? "#4ade80" : "#f87171",
            }}>
              {invoice.vp_decision.toUpperCase()}
            </div>
            {invoice.vp_note && <div style={styles.vpNote}>{invoice.vp_note}</div>}
          </div>
        )}

        {/* Payment Reference */}
        {invoice.payment_reference && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>PAYMENT REFERENCE</div>
            <div style={styles.payRef}>{invoice.payment_reference}</div>
          </div>
        )}

        {/* Rejection Reason */}
        {invoice.rejection_reason && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>REJECTION NOTICE</div>
            <div style={styles.rejection}>{invoice.rejection_reason}</div>
          </div>
        )}

        {/* Audit Trail */}
        {invoice.audit_trail && invoice.audit_trail.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>AUDIT TRAIL</div>
            <div style={styles.auditList}>
              {invoice.audit_trail.map((entry: any, i: number) => (
                <div key={i} style={styles.auditEntry}>
                  <div style={styles.auditMeta}>
                    <span style={styles.auditAgent}>{entry.agent}</span>
                    <span style={styles.auditTime}>
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div style={styles.auditMsg}>{entry.message}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  panel: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  empty: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  emptyIcon: {
    fontSize: 32,
    color: "#222",
  },
  emptyText: {
    color: "#333",
    fontSize: 13,
    fontFamily: "'DM Mono', monospace",
  },
  spinner: {
    width: 24,
    height: 24,
    border: "2px solid #1a1a1a",
    borderTop: "2px solid #555",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    padding: "24px 32px",
    borderBottom: "1px solid #1a1a1a",
  },
  invoiceNum: {
    fontSize: 20,
    fontFamily: "'Syne', sans-serif",
    fontWeight: 800,
    color: "#f0f0f0",
    marginBottom: 4,
  },
  vendor: {
    fontSize: 13,
    color: "#555",
    fontFamily: "'DM Mono', monospace",
  },
  amount: {
    fontSize: 24,
    fontFamily: "'Syne', sans-serif",
    fontWeight: 700,
    color: "#f0f0f0",
    marginBottom: 6,
  },
  stagePill: {
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    letterSpacing: "0.08em",
    border: "1px solid",
    padding: "3px 10px",
    borderRadius: 3,
    display: "inline-block",
  },
  body: {
    flex: 1,
    overflowY: "auto",
    padding: "24px 32px",
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    color: "#444",
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    marginBottom: 12,
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  confidence: {
    background: "#111",
    border: "1px solid #222",
    color: "#666",
    padding: "2px 8px",
    borderRadius: 3,
    fontSize: 10,
  },
  flagDetails: {
    marginTop: 10,
  },
  flagDetail: {
    fontSize: 12,
    fontFamily: "'DM Mono', monospace",
    color: "#f87171",
    marginBottom: 4,
    paddingLeft: 4,
  },
  reasoning: {
    fontSize: 13,
    color: "#aaa",
    lineHeight: 1.7,
    fontFamily: "'DM Mono', monospace",
    background: "#0d0d0d",
    border: "1px solid #1a1a1a",
    borderRadius: 6,
    padding: "16px 20px",
    whiteSpace: "pre-wrap",
  },
  vpDecision: {
    fontSize: 18,
    fontFamily: "'Syne', sans-serif",
    fontWeight: 800,
    marginBottom: 8,
  },
  vpNote: {
    fontSize: 13,
    color: "#666",
    fontFamily: "'DM Mono', monospace",
    fontStyle: "italic",
  },
  payRef: {
    fontSize: 14,
    fontFamily: "'DM Mono', monospace",
    color: "#4ade80",
    letterSpacing: "0.05em",
  },
  rejection: {
    fontSize: 13,
    color: "#888",
    fontFamily: "'DM Mono', monospace",
    lineHeight: 1.7,
    background: "#110a0a",
    border: "1px solid #2d1111",
    borderRadius: 6,
    padding: "16px 20px",
    whiteSpace: "pre-wrap",
  },
  auditList: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  auditEntry: {
    background: "#0d0d0d",
    border: "1px solid #1a1a1a",
    borderRadius: 4,
    padding: "10px 14px",
  },
  auditMeta: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  auditAgent: {
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    color: "#60a5fa",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  auditTime: {
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    color: "#333",
  },
  auditMsg: {
    fontSize: 12,
    fontFamily: "'DM Mono', monospace",
    color: "#666",
    lineHeight: 1.5,
  },
};
