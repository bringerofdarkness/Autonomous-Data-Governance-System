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
  if (score >= 75) return "High Risk";
  if (score >= 40) return "Medium Risk";
  return "Low Risk";
}

function riskLabel(score: number | null | undefined) {
  if (score === null || score === undefined) return "Unknown";
  return `${riskLevel(score)} (${score})`;
}

function readableStatus(status: string) {
  if (status === "PAUSED" || status === "WAITING_FOR_ADMIN") {
    return "Needs Admin Review";
  }

  return status.replaceAll("_", " ");
}

function humanizeAction(action: string) {
  const labels: Record<string, string> = {
    DOCUMENT_UPLOADED: "Document uploaded",
    DOCUMENT_PROCESSING_STARTED: "AI governance review started",
    DOCUMENT_PII_DETECTED: "Sensitive data scan completed",
    DOCUMENT_CONFLICT_CHECKED: "Data contradiction check completed",
    DOCUMENT_HITL_PAUSED: "Admin review required",
    DOCUMENT_HITL_APPROVED: "Document approved by Admin",
    DOCUMENT_HITL_REJECTED: "Document rejected by Admin",
    DOCUMENT_INDEXED_IN_QDRANT: "Added to trusted knowledge base",
    DOCUMENT_QDRANT_INTEGRITY_REPAIRED: "Knowledge base record repaired",
  };

  return labels[action] || action.replaceAll("_", " ");
}

function getActionMessage(
  status: string,
  riskScore: number | null | undefined,
  conflictFound: boolean,
  knowledgeAvailable: boolean,
) {
  if (status === "PAUSED" || status === "WAITING_FOR_ADMIN") {
    return "This document is paused because it contains sensitive information or a possible data contradiction. An Admin must review it before employees can use it as trusted company knowledge.";
  }

  if (status === "APPROVED" && knowledgeAvailable) {
    return "This document has been approved and is already available in the trusted company knowledge base.";
  }

  if (status === "APPROVED" && !knowledgeAvailable) {
    return "This document is approved, but it has not yet been added to the trusted company knowledge base.";
  }

  if (status === "REJECTED") {
    return "This document was rejected and should not be used as trusted company knowledge.";
  }

  if ((riskScore ?? 0) >= 75 || conflictFound) {
    return "This document contains high-risk governance signals and should be reviewed carefully before use.";
  }

  return "No immediate governance action is required.";
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
        error instanceof Error
          ? error.message
          : "Could not load document detail.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function autoLoadDetail() {
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

        if (!isMounted) return;

        setDocument(statusResult);
        setAuditLogs(auditResult);

        try {
          const chunksResult = await getDocumentQdrantChunks(token, documentId);

          if (isMounted) {
            setQdrantChunks(chunksResult);
          }
        } catch {
          if (isMounted) {
            setQdrantChunks(null);
          }
        }
      } catch (error) {
        if (!isMounted) return;

        setDocument(null);
        setAuditLogs([]);
        setQdrantChunks(null);
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Could not load document detail.",
        );
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void autoLoadDetail();

    return () => {
      isMounted = false;
    };
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

    const governanceNotes = asArray(structuredProfile?.governance_notes).filter(
      (item): item is string => typeof item === "string",
    );

    const riskFactors = asArray(riskResult?.risk_factors).filter(
      (item): item is string => typeof item === "string",
    );

    return {
      piiCount: asNumber(piiSummary?.pii_count),
      piiTypes,
      sensitiveFields,
      governanceNotes,
      riskFactors,
      scoreBreakdown,
    };
  }, [auditLogs]);

  const orderedAuditLogs = [...auditLogs].sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );

  if (loading && !document) {
    return (
      <section className="page-section">
        <div className="review-loading-card">Loading governance review...</div>
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

  const actionMessage = getActionMessage(
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
          <div className="review-console-hero">
            <div className="review-console-copy">
              <p className="review-console-eyebrow">Governance Review Console</p>
              <h2>{displayFilename}</h2>
              <p>
                This page explains whether this document is safe for company use,
                what sensitive information was found, whether it conflicts with
                existing trusted knowledge, and what action is required.
              </p>
            </div>

            <div className="review-console-badges">
              <span className="review-status-badge">
                {readableStatus(displayStatus)}
              </span>

              <span className="review-risk-badge">
                {riskLabel(document.risk_score)}
              </span>
            </div>
          </div>

          <div className="review-summary-grid">
            <div className="review-summary-card review-summary-warning">
              <span>Current Status</span>
              <strong>{readableStatus(displayStatus)}</strong>
            </div>

            <div className="review-summary-card review-summary-danger">
              <span>Risk Level</span>
              <strong>{riskLabel(document.risk_score)}</strong>
            </div>

            <div className="review-summary-card review-summary-orange">
              <span>Data Contradiction</span>
              <strong>{document.conflict_found ? "Yes" : "No"}</strong>
            </div>

            <div className="review-summary-card review-summary-neutral">
              <span>Trusted Knowledge</span>
              <strong>{knowledgeAvailable ? "Available" : "Not Available"}</strong>
            </div>
          </div>

          <div className="review-meaning-card">
            <span>What this means</span>
            <p>{actionMessage}</p>
          </div>

          <div className="review-main-grid">
            <div className="review-panel">
              <h3>Document Information</h3>

              <dl className="review-definition-list">
                <div>
                  <dt>Document ID</dt>
                  <dd>{displayDocumentId}</dd>
                </div>

                <div>
                  <dt>Category</dt>
                  <dd>{document.document_category || "-"}</dd>
                </div>

                <div>
                  <dt>Created</dt>
                  <dd>{formatDate(document.created_at)}</dd>
                </div>

                <div>
                  <dt>Processing Message</dt>
                  <dd>{document.error_message || "No active processing error."}</dd>
                </div>
              </dl>
            </div>

            <div className="review-panel review-panel-wide">
              <div className="review-panel-header">
                <div>
                  <h3>Sensitive Data Found</h3>
                  <p>
                    The system found {governanceData.piiCount ?? 0} sensitive
                    item(s). Raw sensitive values are not stored in audit logs.
                  </p>
                </div>

                <span className="review-pii-alert">PII Detected</span>
              </div>

              <div className="review-chip-grid">
                {governanceData.piiTypes &&
                Object.entries(governanceData.piiTypes).length > 0 ? (
                  Object.entries(governanceData.piiTypes).map(([type, count]) => (
                    <div className="review-pii-chip" key={type}>
                      <span>{type.replaceAll("_", " ")}</span>
                      <strong>{String(count)}</strong>
                    </div>
                  ))
                ) : (
                  <p className="review-muted">No sensitive categories available.</p>
                )}
              </div>

              <h4 className="review-subtitle">Sensitive Fields</h4>

              <div className="review-field-table">
                <div className="review-field-header">
                  <span>Field Name</span>
                  <span>Type</span>
                </div>

                {governanceData.sensitiveFields.length > 0 ? (
                  governanceData.sensitiveFields.map((field, index) => (
                    <div
                      className="review-field-row"
                      key={`${String(field.field_name)}-${index}`}
                    >
                      <span>{asString(field.field_name) || "Unknown field"}</span>
                      <strong>
                        {asString(field.sensitivity_type)?.replaceAll("_", " ") ||
                          "Sensitive"}
                      </strong>
                    </div>
                  ))
                ) : (
                  <div className="review-field-empty">
                    No structured sensitive fields available.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="review-main-grid">
            <div className="review-panel">
              <h3>Why this document is risky</h3>

              {governanceData.riskFactors.length > 0 ? (
                <ul className="review-risk-list">
                  {governanceData.riskFactors.map((factor) => (
                    <li key={factor}>{factor}</li>
                  ))}
                </ul>
              ) : (
                <p className="review-muted">No risk factor breakdown available.</p>
              )}

              {governanceData.scoreBreakdown &&
                Object.entries(governanceData.scoreBreakdown).length > 0 && (
                  <div className="review-score-grid">
                    {Object.entries(governanceData.scoreBreakdown).map(
                      ([key, value]) => (
                        <div className="review-score-box" key={key}>
                          <span>{key.replaceAll("_", " ")}</span>
                          <strong>{String(value)}</strong>
                        </div>
                      ),
                    )}
                  </div>
                )}
            </div>

            <div className="review-panel">
              <h3>Data Contradiction</h3>

              <div className="review-conflict-card">
                <strong>
                  {document.conflict_found
                    ? "Contradiction Found"
                    : "No Contradiction"}
                </strong>
                <p>
                  {document.conflict_summary ||
                    "No contradiction summary was provided by the governance engine."}
                </p>
              </div>
            </div>
          </div>

          {governanceData.governanceNotes.length > 0 && (
            <div className="review-panel">
              <div className="review-section-title-row">
                <h3>Governance Notes</h3>
                <span>{governanceData.governanceNotes.length} note(s)</span>
              </div>

              <div className="review-note-list">
                {governanceData.governanceNotes.map((note, index) => (
                  <div className="review-note-card" key={`${note}-${index}`}>
                    {note}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="review-panel">
            <div className="review-section-title-row">
              <div>
                <h3>Governance Timeline</h3>
                <p>Chronological audit trail from upload to review decision.</p>
              </div>
              <span>{orderedAuditLogs.length} event(s)</span>
            </div>

            <div className="review-timeline">
              {orderedAuditLogs.length === 0 ? (
                <div className="review-empty-state">No governance events found.</div>
              ) : (
                orderedAuditLogs.map((log, index) => (
                  <div className="review-timeline-item" key={log.id}>
                    <div className="review-timeline-number">{index + 1}</div>

                    <div className="review-timeline-card">
                      <div className="review-timeline-header">
                        <strong>{humanizeAction(log.action)}</strong>
                        <span>{formatDate(log.created_at)}</span>
                      </div>

                      <p>{log.message || "No message provided."}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="review-panel">
            <div className="review-section-title-row">
              <div>
                <h3>Trusted Knowledge Preview</h3>
                <p>
                  Only approved and redacted content should become searchable
                  company knowledge.
                </p>
              </div>
              <span>{qdrantChunks?.chunks_count ?? 0} chunk(s)</span>
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
              <div className="review-empty-state">
                This document is not currently available in the trusted
                knowledge base. It must be approved before employees can use it
                as trusted company knowledge.
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}