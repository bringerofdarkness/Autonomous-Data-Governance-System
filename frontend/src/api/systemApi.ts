import { apiRequest } from "./client";

export type SystemAuditSummary = {
  generated_at: string;
  documents: {
    total: number;
    uploaded: number;
    processing: number;
    paused: number;
    waiting_for_admin: number;
    approved: number;
    rejected: number;
    failed: number;
    indexed: number;
    conflict_found: number;
    high_risk: number;
    created_last_24h: number;
  };
  rag: {
    total_searches: number;
    searches_last_24h: number;
  };
  audit_logs: {
    document_audit_logs_total: number;
    document_audit_logs_last_24h: number;
  };
};

export function getSystemAuditSummary(token: string) {
  return apiRequest<SystemAuditSummary>("/system/audit-summary", {
    token,
  });
}
