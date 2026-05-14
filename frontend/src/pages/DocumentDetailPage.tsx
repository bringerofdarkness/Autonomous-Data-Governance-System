import { useEffect, useMemo, useState } from "react";
import {
  getDocumentAuditLogs,
  getDocumentQdrantChunks,
  getDocumentStatus,
  type DocumentAuditLog,
  type DocumentQdrantChunksResponse,
  type DocumentStatusDetail,
} from "../api/documentsApi";

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function riskLevel(score: number | null | undefined) {
  if (score === null || score === undefined) return "Unknown";
  if (score >= 75) return "High";
  if (score >= 40) return "Medium";
  return "Low";
}

function riskLabel(score: number | null | undefined) {
  if (score === null || score === undefined) return "Unknown";
  return `${riskLevel(score)} Risk (${score})`;
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

function humanizeAction(action: string) {
  const labels: Record<string, string> = {
    DOCUMENT_UPLOADED: "Document uploaded",
    DOCUMENT_PROCESSING_STARTED: "Governance processing started",
    DOCUMENT_PII_DETECTED: "Sensitive data scan completed",
    DOCUMENT_CONFLICT_CHECKED: "Data contradiction check completed",
    DOCUMENT_HITL_PAUSED: "Admin review required",
    DOCUMENT_HITL_APPROVED: "Document approved by Admin",
    DOCUMENT_HITL_REJECTED: "Document rejected by Admin",
    DOCUMENT_INDEXED_IN_QDRANT: "Added to trusted knowledge base",
    DOCUMENT_QDRANT_INTEGRITY_REPAIRED: "Knowledge base indexing record repaired",
  };

  return labels[action] || action.replaceAll("_", " ").toLowerCase();
}

function getRecommendation(
  status: string,
  riskScore: number | null | undefined,
  conflictFound: boolean,
  knowledgeAvailable: boolean,
) {
  if (status === "PAUSED" || status === "WAITING_FOR_ADMIN") {
    return "This document needs Admin review before it can become trusted company knowledge.";
  }

  if (status === "APPROVED" && !knowledgeAvailable) {
    return "This document is approved but not available in the trusted knowledge base yet.";
  }

  if (status === "APPROVED" && knowledgeAvailable) {
    return "This document is approved and available for trusted retrieval.";
  }

  if (status === "REJECTED") {
    return "This document was rejected and should not be used as trusted knowledge.";
  }

  if ((riskScore ?? 0) >= 75 || conflictFound) {
    return "This document should be reviewed carefully because it contains high-risk signals.";
  }

  return "No immediate action is required.";
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

      const [statusResult, auditResult] = await Promise.all([
        getDocumentStatus(token, documentId),
        getDocumentAuditLogs(token, documentId),
      ]);

      setDocument(statusResult);
      setAuditLogs(auditResult);

      try {
        const chunksResult = await getDocumentQdrantChunks(token, documentId);
        setQdrantChunks(chunksResult);
      } catch {
        setQdrantChunks(null);
      }
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

  const governanceData = useMemo(() => {
    const piiLog = auditLogs.find((log) => {
      const extraData = asRecord(log.extra_data);
      return Boolean(extraData?.pii_summary || extraData?.risk_result);
    });

    const extraData = asRecord(piiLog?.extra_data);
    const piiSummary = asRecord(extraData?.pii_summary);
    const piiTypes = asRecord(piiSummary?.pii_types);
    const structuredProfile = asRecord(extraData?.structured_profile);
    const riskResult = asRecord(extraData?.risk_result);
    const scoreBreakdown = asRecord(riskResult?.score_breakdown);

    const sensitiveFields = asArray(structuredProfile?.sensitive_fields)
      .map(asRecord)
      .filter((item): item is Record<string, unknown> => item !== null);

    const governanceNotes = asArray(structuredProfile?.governance_notes)
      .filter((item): item is string => typeof item === "string");

    const riskFactors = asArray(riskResult?.risk_factors)
      .filter((item): item is string => typeof item === "string");

    return {
      piiCount: asNumber(piiSummary?.pii_count),
      piiTypes,
      sensitiveFields,
      governanceNotes,
      riskFactors,
      scoreBreakdown,
    };
  }, [auditLogs]);

  if (loading && !document) {
    return (
      <section className="page-section">
        <div className="table-card">
          <div className="empty-state">Loading governance review...</div>
        </div>
      </section>
    );
  }

  const displayStatus =
    document?.status || document?.database_status || "UNKNOWN";

  const displayDocumentId = document?.document_id || document?.id || documentId;
  const displayFilename =
    document?.original_filename || qdrantChunks?.original_filename || "Document";

  const knowledgeAvailable = Boolean(
    document?.qdrant_point_id || qdrantChunks?.indexed,
  );

  const recommendation = getRecommendation(
    displayStatus,
    document?.risk_score,
    Boolean(document?.conflict_found),
    knowledgeAvailable,
  );

  return (
    <section className="page-section">
      <div className="detail-toolbar">
        <button className="secondary-button" onClick={onBack}>
          Back to Documents
        </button>

        <button className="primary-button" onClick={loadDetail} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh Review"}
        </button>
      </div>

      {errorMessage && <p className="error-message">{errorMessage}</p>}

      {document && (
        <>
          <div className="hero-panel">
            <div>
              <h2>{displayFilename}</h2>
              <p>
                This review explains the document risk, sensitive data exposure,
                contradiction status, and trusted knowledge availability.
              </p>
            </div>

            <div className="detail-badge-row">
              <span className={statusClass(displayStatus)}>
                {displayStatus.replaceAll("_", " ")}
              </span>

              <span className={riskClass(document.risk_score)}>
                {riskLabel(document.risk_score)}
              </span>
            </div>
          </div>

          <div className="review-summary-grid">
            <div className="review-summary-card">
              <span>Document Status</span>
              <strong>{displayStatus.replaceAll("_", " ")}</strong>
            </div>

            <div className="review-summary-card">
              <span>Risk Level</span>
              <strong>{riskLabel(document.risk_score)}</strong>
            </div>

            <div className="review-summary-card">
              <span>Data Contradiction</span>
              <strong>{document.conflict_found ? "Yes" : "No"}</strong>
            </div>

            <div className="review-summary-card">
              <span>Knowledge Base</span>
              <strong>{knowledgeAvailable ? "Available" : "Not Available"}</strong>
            </div>
          </div>

          <div className="recommendation-card">
            <span>Recommended Governance Action</span>
            <p>{recommendation}</p>
          </div>

          <div className="detail-grid">
            <div className="detail-card">
              <h3>Document Overview</h3>

              <dl>
                <dt>Document ID</dt>
                <dd>{displayDocumentId}</dd>

                <dt>Category</dt>
                <dd>{document.document_category || "-"}</dd>

                <dt>Created</dt>
                <dd>{formatDate(document.created_at)}</dd>

                <dt>Updated</dt>
                <dd>{formatDate(document.updated_at)}</dd>

                <dt>Processing Message</dt>
                <dd>{document.error_message || "No active processing error."}</dd>
              </dl>
            </div>

            <div className="detail-card">
              <h3>Sensitive Data Profile</h3>

              <dl>
                <dt>Sensitive Data Items</dt>
                <dd>{governanceData.piiCount ?? 0}</dd>

                <dt>Detected Types</dt>
                <dd>
                  <div className="pill-list">
                    {governanceData.piiTypes &&
                    Object.entries(governanceData.piiTypes).length > 0 ? (
                      Object.entries(governanceData.piiTypes).map(([type, count]) => (
                        <span className="info-pill" key={type}>
                          {type.replaceAll("_", " ")}: {String(count)}
                        </span>
                      ))
                    ) : (
                      "-"
                    )}
                  </div>
                </dd>

                <dt>Sensitive Fields</dt>
                <dd>
                  <div className="pill-list">
                    {governanceData.sensitiveFields.length > 0 ? (
                      governanceData.sensitiveFields.map((field, index) => (
                        <span className="info-pill" key={`${String(field.field_name)}-${index}`}>
                          {asString(field.field_name) || "Unknown field"} ·{" "}
                          {asString(field.sensitivity_type) || "Sensitive"}
                        </span>
                      ))
                    ) : (
                      "-"
                    )}
                  </div>
                </dd>
              </dl>
            </div>

            <div className="detail-card">
              <h3>Risk Explanation</h3>

              {governanceData.riskFactors.length > 0 ? (
                <ul className="risk-factor-list">
                  {governanceData.riskFactors.map((factor) => (
                    <li key={factor}>{factor}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted-copy">No risk factor breakdown available.</p>
              )}

              {governanceData.scoreBreakdown &&
                Object.entries(governanceData.scoreBreakdown).length > 0 && (
                  <div className="score-grid">
                    {Object.entries(governanceData.scoreBreakdown).map(
                      ([key, value]) => (
                        <div className="score-item" key={key}>
                          <span>{key.replaceAll("_", " ")}</span>
                          <strong>{String(value)}</strong>
                        </div>
                      ),
                    )}
                  </div>
                )}
            </div>

            <div className="detail-card">
              <h3>Knowledge Base Status</h3>

              <dl>
                <dt>Availability</dt>
                <dd>{knowledgeAvailable ? "Available" : "Not Available"}</dd>

                <dt>Indexed At</dt>
                <dd>{formatDate(document.indexed_at)}</dd>

                <dt>Available Chunks</dt>
                <dd>{qdrantChunks?.chunks_count ?? 0}</dd>

                <dt>Purpose</dt>
                <dd>
                  Only approved and redacted documents should become trusted
                  knowledge for retrieval.
                </dd>
              </dl>
            </div>
          </div>

          {governanceData.governanceNotes.length > 0 && (
            <div className="table-card">
              <div className="table-header">
                <h2>Governance Notes</h2>
                <p>{governanceData.governanceNotes.length} note(s)</p>
              </div>

              <div className="note-list">
                {governanceData.governanceNotes.map((note) => (
                  <div className="note-card" key={note}>
                    {note}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="table-card">
            <div className="table-header">
              <h2>Governance Timeline</h2>
              <p>{auditLogs.length} event(s)</p>
            </div>

            <div className="timeline-list">
              {auditLogs.length === 0 ? (
                <div className="empty-state">No governance events found.</div>
              ) : (
                auditLogs.map((log) => (
                  <div className="timeline-item" key={log.id}>
                    <div className="timeline-dot" />

                    <div>
                      <div className="timeline-title">
                        {humanizeAction(log.action)}
                      </div>
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
              <h2>Trusted Knowledge Preview</h2>
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
                This document is not currently available in the trusted
                knowledge base.
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
