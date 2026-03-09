const BASE = "/api/v1";

export interface Metrics {
  total: number;
  approved: number;
  rejected: number;
  pending_vp: number;
  processing: number;
  failed: number;
  approval_rate: number;
  rejection_rate: number;
  total_paid: number;
  total_rejected_value: number;
  average_invoice_value: number;
}

export interface InvoiceSummary {
  invoice_number: string;
  vendor: string;
  total: number;
  currency: string;
  current_stage: string;
  payment_status: string | null;
  requires_vp_approval: boolean;
  rejection_reason: string | null;
}

export interface InvoiceDetail extends InvoiceSummary {
  file_path: string;
  finance_reasoning: string | null;
  finance_confidence: number | null;
  validation_flags: {
    is_fraudulent: boolean;
    is_out_of_stock: boolean;
    is_unknown_item: boolean;
    is_data_integrity_issue: boolean;
    is_quantity_mismatch: boolean;
    is_total_mismatch: boolean;
    details: string[];
  } | null;
  audit_trail: {
    timestamp: string;
    agent: string;
    action: string;
    message: string;
  }[];
  vp_decision: string | null;
  vp_note: string | null;
  payment_reference: string | null;
}

export const api = {
  async getMetrics(): Promise<Metrics> {
    const res = await fetch(`${BASE}/metrics`);
    return res.json();
  },

  async getInvoices(): Promise<{ invoices: InvoiceSummary[]; total: number }> {
    const res = await fetch(`${BASE}/invoices`);
    return res.json();
  },

  async getInvoice(invoiceNumber: string): Promise<InvoiceDetail> {
    const res = await fetch(`${BASE}/invoices/${invoiceNumber}`);
    return res.json();
  },

  async processInvoice(filePath: string): Promise<{ message: string; status: string }> {
    const res = await fetch(`${BASE}/invoices/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_path: filePath }),
    });
    return res.json();
  },

  async getPendingApprovals(): Promise<{ approvals: InvoiceSummary[]; total: number }> {
    const res = await fetch(`${BASE}/approvals/pending`);
    return res.json();
  },

  async submitVPDecision(
    invoiceNumber: string,
    decision: "approve" | "reject",
    note?: string
  ): Promise<any> {
    const res = await fetch(`${BASE}/approvals/${invoiceNumber}/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, note: note || "" }),
    });
    return res.json();
  },
};
