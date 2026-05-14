import { useEffect, useState } from "react";
import {
  getDocumentAuditLogs,
  getDocumentQdrantChunks,
  getDocumentStatus,
  type DocumentAuditLog,
  type DocumentQdrantChunksResponse,
  type DocumentStatusDetail,
} from "../api/documentsApi";

function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function riskLabel(score: number | null | undefined) {
  if (score === null || score === undefined) return "UNKNOWN";
  if (score >= 75) return `HIGH ${score}`;
  if (score >= 40) return `MEDIUM ${score}`;
  return `LOW ${score}`;
}

function riskClass(score: number | null | undefined) {
  if (score === null || score === undefined) return "risk-badge risk-unknown";
  if (score >= 75) return "risk-badge risk-high";
  if (score >= 40) return "risk-badge risk-medium";
  return "risk-badge risk-low";
}

function statusClass(status: string | undefined) {
  if (status === "APPROVED") return "status-badge status-approved";
  if (status === "PAUSED" || status === "WAITING_FOR_ADMIN") {
    return "status-badge status-warning";
  }
  if (status === "REJECTED" || status === "FAILED") {
    return "status-badge status-danger";
  }
  if (status === "PROCESSING") return "status-badge status-processing";
  return "status-badge status-neutral";
}

export function DocumentDetailPage({
  documentId,
  onBack,
}: {
  documentId: string;
  onBack: () => void;
}) {
  const [document, setDocument] = useState<DocumentStatusDetail | null>(null);
  const [auditLogs, setAuditLogs] = useState<DocumentAuditLog[]>([]);
  const [qdrantChunks, setQdrantChunks] =
    useState<DocumentQdrantChunksResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadDetail() {
    try {
      setLoading(true);
      setErrorMessage("");

      const token = localStorage.getItem("adgs_access_token");

      if (!token) {
        throw new Error("Please login from the Dashboard page first.");
      }

      const [statusResult, auditResult, chunksResult] = await Promise.all([
        getDocumentStatus(token, documentId),
        getDocumentAuditLogs(token, documentId),
        getDocumentQdrantChunks(token, documentId),
      ]);

      setDocument(statusResult);
      setAuditLogs(auditResult);
      setQdrantChunks(chunksResult);
    } catch (error) {
      setDocument(null);
      setAuditLogs([]);
      setQdrantChunks(null);
      setErrorMessage(
        error instanceof Error ? error.message : "Could not load document detail.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDetail();
  }, [documentId]);

  return (
    <section className="page-section">
      <div className="detail-toolbar">
        <button className="secondary-button" onClick={onBack}>
          Back to Documents
        </button>

        <button className="primary-button" onClick={loadDetail} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh Detail"}
        </button>
      </div>

      {errorMessage && <p className="error-message">{errorMessage}</p>}

      {document && (
        <>
          <div className="hero-panel">
            <div>
              <h2>{document.original_filename}</h2>
              <p>
                Document ID: <strong>{document.id}</strong>
              </p>
            </div>

            <div className="detail-badge-row">
              <span className={statusClass(document.status)}>
                {document.status}
              </span>

              <span className={riskClass(document.risk_score)}>
                {riskLabel(document.risk_score)}
              </span>
            </div>
          </div>

          <div className="detail-grid">
            <div className="detail-card">
              <h3>Governance Metadata</h3>

              <dl>
                <dt>Category</dt>
                <dd>{document.document_category || "-"}</dd>

                <dt>Content Type</dt>
                <dd>{document.content_type || "-"}</dd>

                <dt>File Size</dt>
                <dd>{document.file_size_bytes} bytes</dd>

                <dt>Created</dt>
                <dd>{formatDate(document.created_at)}</dd>

                <dt>Updated</dt>
                <dd>{formatDate(document.updated_at)}</dd>
              </dl>
            </div>

            <div className="detail-card">
              <h3>Risk & Conflict</h3>

              <dl>
                <dt>Risk Score</dt>
                <dd>
                  <span className={riskClass(document.risk_score)}>
                    {riskLabel(document.risk_score)}
                  </span>
                </dd>

                <dt>Conflict Found</dt>
                <dd>{document.conflict_found ? "Yes" : "No"}</dd>

                <dt>Conflict Checked At</dt>
                <dd>{formatDate(document.conflict_checked_at)}</dd>

                <dt>Conflict Summary</dt>
                <dd>{document.conflict_summary || "-"}</dd>
              </dl>
            </div>

            <div className="detail-card">
              <h3>Qdrant Gold Index</h3>

              <dl>
                <dt>Indexed</dt>
                <dd>{document.qdrant_point_id ? "Yes" : "No"}</dd>

                <dt>Qdrant Point ID</dt>
                <dd>{document.qdrant_point_id || "-"}</dd>

                <dt>Indexed At</dt>
                <dd>{formatDate(document.indexed_at)}</dd>

                <dt>Chunk Count</dt>
                <dd>{qdrantChunks?.chunks_count ?? 0}</dd>
              </dl>
            </div>
          </div>

          <div className="table-card">
            <div className="table-header">
              <h2>Audit Timeline</h2>
              <p>{auditLogs.length} event(s)</p>
            </div>

            <div className="timeline-list">
              {auditLogs.length === 0 ? (
                <div className="empty-state">No audit logs found.</div>
              ) : (
                auditLogs.map((log) => (
                  <div className="timeline-item" key={log.id}>
                    <div className="timeline-dot" />

                    <div>
                      <div className="timeline-title">{log.action}</div>
                      <p>{log.message || "No message provided."}</p>
                      <small>{formatDate(log.created_at)}</small>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="table-card">
            <div className="table-header">
              <h2>Qdrant Chunks</h2>
              <p>{qdrantChunks?.chunks_count ?? 0} chunk(s)</p>
            </div>

            {qdrantChunks && qdrantChunks.chunks.length > 0 ? (
              <div className="chunk-list">
                {qdrantChunks.chunks.map((chunk) => (
                  <div className="chunk-card" key={chunk.point_id}>
                    <div className="chunk-meta">
                      <strong>Chunk {chunk.chunk_index ?? "-"}</strong>
                      <span>{chunk.char_count ?? 0} characters</span>
                    </div>

                    <p>{chunk.chunk_text || "No chunk text available."}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                No Qdrant chunks found for this document.
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
