import { apiRequest } from "./client";

export type DocumentStatus =
  | "UPLOADED"
  | "PROCESSING"
  | "PAUSED"
  | "WAITING_FOR_ADMIN"
  | "APPROVED"
  | "REJECTED"
  | "FAILED";

export type DocumentListItem = {
  id: string;
  original_filename: string;
  stored_filename: string;
  cleaned_text_filename: string | null;
  content_type: string | null;
  file_size_bytes: number;
  status: DocumentStatus;
  document_category: string | null;
  risk_score: number | null;
  conflict_found: boolean;
  conflict_summary: string | null;
  conflict_checked_at: string | null;
  qdrant_point_id: string | null;
  indexed_at: string | null;
  celery_task_id: string | null;
  uploaded_by_id: string;
  created_at: string;
  updated_at: string;
};

export type DocumentListFilters = {
  status?: string;
  document_category?: string;
  min_risk_score?: string;
  max_risk_score?: string;
  conflict_found?: string;
  indexed?: string;
  limit?: string;
  offset?: string;
};

export function getDocuments(
  token: string,
  filters: DocumentListFilters,
) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      params.append(key, value);
    }
  });

  const queryString = params.toString();
  const path = queryString ? `/documents?${queryString}` : "/documents";

  return apiRequest<DocumentListItem[]>(path, {
    token,
  });
}
