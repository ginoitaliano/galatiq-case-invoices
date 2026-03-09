import React, { useState, useEffect, useCallback } from "react";
import { api, Metrics, InvoiceSummary, InvoiceDetail } from "./api/client";
import { MetricsBar } from "./components/MetricsBar";
import { InvoiceQueue } from "./components/InvoiceQueue";
import { InvoiceDetailPanel } from "./components/InvoiceDetail";
import { VPApprovalPanel } from "./components/VPApprovalPanel";

const EMPTY_METRICS: Metrics = {
  total: 0, approved: 0, rejected: 0, pending_vp: 0, processing: 0, failed: 0,
  approval_rate: 0, rejection_rate: 0, total_paid: 0, total_rejected_value: 0, average_invoice_value: 0,
};

export default function App() {
  const [metrics, setMetrics] = useState<Metrics>(EMPTY_METRICS);
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [approvals, setApprovals] = useState<InvoiceSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<InvoiceDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const refresh = useCallback(async () => {
    const [m, inv, apr] = await Promise.all([
      api.getMetrics(),
      api.getInvoices(),
      api.getPendingApprovals(),
    ]);
    setMetrics(m);
    setInvoices(inv.invoices || []);
    setApprovals(apr.approvals || []);
  }, []);

  // Poll every 5 seconds to catch pipeline completions
  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  // Load detail when selection changes
  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    setDetailLoading(true);
    api.getInvoice(selectedId)
      .then(setDetail)
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  // Re-fetch detail when invoices update (pipeline may have progressed)
  useEffect(() => {
    if (!selectedId) return;
    api.getInvoice(selectedId).then(setDetail);
  }, [invoices, selectedId]);

  const handleProcess = async (filePath: string) => {
    await api.processInvoice(filePath);
    setTimeout(refresh, 2000);
  };

  return (
    <div style={styles.root}>
      {/* Inject Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080808; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0a0a0a; }
        ::-webkit-scrollbar-thumb { background: #1a1a1a; border-radius: 2px; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

      {/* Top bar */}
      <div style={styles.topBar}>
        <div style={styles.logo}>
          <span style={styles.logoMark}>◆</span>
          <span style={styles.logoText}>GALATIQ</span>
          <span style={styles.logoSub}>Invoice Intelligence</span>
        </div>
        <div style={styles.liveIndicator}>
          <span style={styles.liveDot} />
          LIVE
        </div>
      </div>

      {/* Metrics strip */}
      <MetricsBar metrics={metrics} />

      {/* Main layout */}
      <div style={styles.main}>
        <InvoiceQueue
          invoices={invoices}
          selected={selectedId}
          onSelect={setSelectedId}
          onProcess={handleProcess}
        />
        <InvoiceDetailPanel invoice={detail} loading={detailLoading} />
        <VPApprovalPanel approvals={approvals} onDecision={refresh} />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    background: "#080808",
    fontFamily: "'DM Mono', monospace",
    color: "#f0f0f0",
    overflow: "hidden",
  },
  topBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "14px 24px",
    borderBottom: "1px solid #1a1a1a",
    background: "#080808",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  logoMark: {
    color: "#f0f0f0",
    fontSize: 14,
  },
  logoText: {
    fontSize: 14,
    fontFamily: "'Syne', sans-serif",
    fontWeight: 800,
    color: "#f0f0f0",
    letterSpacing: "0.15em",
  },
  logoSub: {
    fontSize: 11,
    color: "#333",
    fontFamily: "'DM Mono', monospace",
    paddingLeft: 10,
    borderLeft: "1px solid #1a1a1a",
    marginLeft: 2,
  },
  liveIndicator: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    color: "#333",
    letterSpacing: "0.1em",
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#4ade80",
    boxShadow: "0 0 6px #4ade80",
    animation: "pulse 2s infinite",
  },
  main: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
  },
};
