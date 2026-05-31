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
  uploaded_by_id?: string;
  created_from?: string;
  created_to?: string;
  limit?: string;
  offset?: string;
};

export type DocumentStatusDetail = Partial<DocumentListItem> & {
  document_id?: string;
  database_status?: string;
  celery_state?: string | null;
  celery_result?: unknown;
  error_message?: string | null;
};

export type DocumentAuditLog = {
  id: string;
  document_id: string;
  actor_user_id: string | null;
  action: string;
  message: string | null;
  extra_data: Record<string, unknown> | null;
  created_at: string;
};

export type QdrantChunk = {
  point_id: string;
  chunk_index: number | null;
  chunk_text: string | null;
  char_count: number | null;
  payload: Record<string, unknown> | null;
};

export type DocumentQdrantChunksResponse = {
  document_id: string;
  original_filename: string;
  indexed: boolean;
  chunks_count: number;
  chunks: QdrantChunk[];
  message: string;
};

export type AdminDecisionPayload = {
  decision: "approve" | "reject";
};

// 1. Fetch filtered document list
export function getDocuments(token: string, filters: DocumentListFilters) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      params.append(key, value);
    }
  });

  const queryString = params.toString();
  const path = queryString ? `/documents?${queryString}` : "/documents";

  return apiRequest<DocumentListItem[]>(path, { token });
}

// 2. Fetch specific document status
export function getDocumentStatus(token: string, documentId: string) {
  return apiRequest<DocumentStatusDetail>(`/documents/${documentId}/status`, {
    token,
  });
}

// 3. Fetch audit logs
export function getDocumentAuditLogs(token: string, documentId: string) {
  return apiRequest<DocumentAuditLog[]>(
    `/documents/${documentId}/audit-logs?limit=50&offset=0`,
    { token }
  );
}

// 4. Fetch indexed chunks from Qdrant
export function getDocumentQdrantChunks(token: string, documentId: string) {
  return apiRequest<DocumentQdrantChunksResponse>(
    `/documents/${documentId}/qdrant-chunks?limit=20`,
    { token }
  );
}

// 5. Upload document (Uses FormData now correctly supported by client)
export function uploadDocument(token: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<DocumentListItem>("/documents/upload", {
    method: "POST",
    token,
    body: formData,
  });
}

// 6. Resume LangGraph workflow via HITL interaction node
export function resumeDocumentWorkflow(
  token: string,
  documentId: string,
  payload: AdminDecisionPayload
) {
  return apiRequest<{ message: string; status: string }>(
    `/documents/${documentId}/resume`,
    {
      method: "POST",
      token,
      body: payload, // Notice: No JSON.stringify here anymore! Passed as raw object.
    }
  );
}

// ==========================================
// RAG INTELLIGENCE HUB EXTENSIONS
// ==========================================

export interface RagChunkMatch {
  point_id: string; // Maps to Qdrant record identifier
  text: string;
  score: number;
  metadata: {
    document_id: string;
    document_category?: string;
    [key: string]: unknown;
  };
}

export interface RagSearchResponse {
  query: string;
  min_score: number;
  matches_count: number;
  matches: RagChunkMatch[];
  synthesized_answer: string | null; // NEW: Receives hallucination-resistant text layer
}

/**
 * 7. Fires a contextual lookup query against the audited gold collection matrices
 */
export function executeRagSearch(
  token: string,
  query: string,
  limit: number = 5,
  minScore: number = 0.5
) {
  // Pass ONLY the relative routing path. The apiRequest client will combine it cleanly.
  return apiRequest<RagSearchResponse>("/rag/search", {
    method: "POST",
    token,
    body: {
      query: query,
      limit: limit,
      min_score: minScore,
    },
  });
}