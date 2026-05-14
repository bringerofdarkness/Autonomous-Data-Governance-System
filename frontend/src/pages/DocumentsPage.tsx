import { useEffect, useState } from "react";
import {
  getDocuments,
  type DocumentListFilters,
  type DocumentListItem,
} from "../api/documentsApi";

const DEFAULT_FILTERS: DocumentListFilters = {
  status: "",
  document_category: "",
  min_risk_score: "",
  max_risk_score: "",
  conflict_found: "",
  indexed: "",
  limit: "20",
  offset: "0",
};

type RiskLevelFilter = "" | "low" | "medium" | "high";

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function statusBadgeClass(status: string) {
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

function riskBadgeClass(riskScore: number | null) {
  if (riskScore === null) return "risk-badge risk-unknown";
  if (riskScore >= 75) return "risk-badge risk-high";
  if (riskScore >= 40) return "risk-badge risk-medium";
  return "risk-badge risk-low";
}

function riskLabel(riskScore: number | null) {
  if (riskScore === null) return "UNKNOWN";
  if (riskScore >= 75) return `HIGH (${riskScore})`;
  if (riskScore >= 40) return `MEDIUM (${riskScore})`;
  return `LOW (${riskScore})`;
}

function booleanBadgeClass(value: boolean, positiveLabel: string) {
  if (value) {
    return positiveLabel === "Indexed"
      ? "boolean-badge boolean-success"
      : "boolean-badge boolean-danger";
  }

  return "boolean-badge boolean-muted";
}

function getRiskScoreRange(riskLevel: RiskLevelFilter) {
  if (riskLevel === "low") {
    return {
      min_risk_score: "0",
      max_risk_score: "39",
    };
  }

  if (riskLevel === "medium") {
    return {
      min_risk_score: "40",
      max_risk_score: "74",
    };
  }

  if (riskLevel === "high") {
    return {
      min_risk_score: "75",
      max_risk_score: "100",
    };
  }

  return {
    min_risk_score: "",
    max_risk_score: "",
  };
}

export function DocumentsPage({
  onOpenDocument,
}: {
  onOpenDocument: (documentId: string) => void;
}) {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

  const [riskLevel, setRiskLevel] = useState<RiskLevelFilter>("");

  const [filters, setFilters] = useState<DocumentListFilters>({
    ...DEFAULT_FILTERS,
  });

  function updateFilter(key: keyof DocumentListFilters, value: string) {
    setFilters((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function buildApiFilters(
    activeFilters: DocumentListFilters,
    activeRiskLevel: RiskLevelFilter,
  ): DocumentListFilters {
    const riskRange = getRiskScoreRange(activeRiskLevel);

    return {
      ...activeFilters,
      min_risk_score: riskRange.min_risk_score,
      max_risk_score: riskRange.max_risk_score,
      limit: "20",
      offset: "0",
    };
  }

  async function loadDocuments(
    activeFilters: DocumentListFilters = filters,
    activeRiskLevel: RiskLevelFilter = riskLevel,
  ) {
    try {
      setLoading(true);
      setErrorMessage("");

      const token = localStorage.getItem("adgs_access_token");

      if (!token) {
        throw new Error("Please login from the Dashboard page first.");
      }

      const apiFilters = buildApiFilters(activeFilters, activeRiskLevel);
      const data = await getDocuments(token, apiFilters);

      setDocuments(data);
      setHasLoadedOnce(true);
    } catch (error) {
      setDocuments([]);
      setHasLoadedOnce(true);
      setErrorMessage(
        error instanceof Error ? error.message : "Could not load documents.",
      );
    } finally {
      setLoading(false);
    }
  }

  function resetFilters() {
    const resetFilterValues = {
      ...DEFAULT_FILTERS,
    };

    setFilters(resetFilterValues);
    setRiskLevel("");

    void loadDocuments(resetFilterValues, "");
  }

useEffect(() => {
  let isMounted = true;

  async function autoLoadDocuments() {
    try {
      setLoading(true);
      setErrorMessage("");

      const token = localStorage.getItem("adgs_access_token");

      if (!token) {
        throw new Error("Please login from the Dashboard page first.");
      }

      const data = await getDocuments(token, DEFAULT_FILTERS);

      if (!isMounted) {
        return;
      }

      setDocuments(data);
      setHasLoadedOnce(true);
    } catch (error) {
      if (!isMounted) {
        return;
      }

      setDocuments([]);
      setHasLoadedOnce(true);
      setErrorMessage(
        error instanceof Error ? error.message : "Could not load documents.",
      );
    } finally {
      if (isMounted) {
        setLoading(false);
      }
    }
  }

  void autoLoadDocuments();

  return () => {
    isMounted = false;
  };
}, []);

  return (
    <section className="page-section">
      <div className="hero-panel">
        <div>
          <h2>Governance Document Registry</h2>
          <p>
            Review company documents by approval status, risk level, data
            contradictions, and knowledge base availability.
          </p>
        </div>

        <div className="system-pill">
          {loading ? "Loading..." : `${documents.length} Loaded`}
        </div>
      </div>

      <div className="filter-card">
        <div className="filter-grid">
          <div>
            <label>Document Status</label>
            <select
              value={filters.status}
              onChange={(event) => updateFilter("status", event.target.value)}
            >
              <option value="">All</option>
              <option value="UPLOADED">Uploaded</option>
              <option value="PROCESSING">Processing</option>
              <option value="PAUSED">Needs Review</option>
              <option value="WAITING_FOR_ADMIN">Waiting for Admin</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>

          <div>
            <label>Document Category</label>
            <input
              value={filters.document_category}
              onChange={(event) =>
                updateFilter("document_category", event.target.value)
              }
              placeholder="Policy"
            />
          </div>

          <div>
            <label>Risk Level</label>
            <select
              value={riskLevel}
              onChange={(event) =>
                setRiskLevel(event.target.value as RiskLevelFilter)
              }
            >
              <option value="">All</option>
              <option value="low">Low Risk (0-39)</option>
              <option value="medium">Medium Risk (40-74)</option>
              <option value="high">High Risk (75-100)</option>
            </select>
          </div>

          <div>
            <label>Data Contradiction</label>
            <select
              value={filters.conflict_found}
              onChange={(event) =>
                updateFilter("conflict_found", event.target.value)
              }
            >
              <option value="">All</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>

          <div>
            <label>Knowledge Base Status</label>
            <select
              value={filters.indexed}
              onChange={(event) => updateFilter("indexed", event.target.value)}
            >
              <option value="">All</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
        </div>

        <div className="button-row">
          <button
            className="primary-button"
            onClick={() => void loadDocuments()}
            disabled={loading}
          >
            {loading ? "Loading..." : "Apply Filters"}
          </button>

          <button className="secondary-button" onClick={resetFilters}>
            Reset Filters
          </button>
        </div>

        {errorMessage && <p className="error-message">{errorMessage}</p>}
      </div>

      <div className="table-card">
        <div className="table-header">
          <h2>Document Results</h2>
          <p>{documents.length} row(s)</p>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>Category</th>
                <th>Risk</th>
                <th>Data Contradiction</th>
                <th>Knowledge Base</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty-state">
                    {loading
                      ? "Loading documents..."
                      : hasLoadedOnce
                        ? "No documents match the selected filters."
                        : "Documents will load automatically."}
                  </td>
                </tr>
              ) : (
                documents.map((document) => (
                  <tr key={document.id}>
                    <td className="filename-cell">
                      <strong>{document.original_filename}</strong>
                      <span>{document.id}</span>
                    </td>

                    <td>
                      <span className={statusBadgeClass(document.status)}>
                        {document.status.replaceAll("_", " ")}
                      </span>
                    </td>

                    <td>{document.document_category || "-"}</td>

                    <td>
                      <span className={riskBadgeClass(document.risk_score)}>
                        {riskLabel(document.risk_score)}
                      </span>
                    </td>

                    <td>
                      <span
                        className={booleanBadgeClass(
                          document.conflict_found,
                          "Conflict",
                        )}
                      >
                        {document.conflict_found ? "Yes" : "No"}
                      </span>
                    </td>

                    <td>
                      <span
                        className={booleanBadgeClass(
                          Boolean(document.qdrant_point_id),
                          "Indexed",
                        )}
                      >
                        {document.qdrant_point_id ? "Available" : "Not Available"}
                      </span>
                    </td>

                    <td>{formatDate(document.created_at)}</td>

                    <td>
                      <button
                        className="mini-button"
                        onClick={() => onOpenDocument(document.id)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}