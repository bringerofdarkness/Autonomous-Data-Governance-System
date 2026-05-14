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
  if (riskScore >= 75) return `HIGH ${riskScore}`;
  if (riskScore >= 40) return `MEDIUM ${riskScore}`;
  return `LOW ${riskScore}`;
}

function booleanBadgeClass(value: boolean, positiveLabel: string) {
  if (value) {
    return positiveLabel === "Indexed"
      ? "boolean-badge boolean-success"
      : "boolean-badge boolean-danger";
  }

  return "boolean-badge boolean-muted";
}

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

  const [filters, setFilters] = useState<DocumentListFilters>(DEFAULT_FILTERS);

  function updateFilter(key: keyof DocumentListFilters, value: string) {
    setFilters((current) => ({
      ...current,
      [key]: value,
    }));
  }

  async function loadDocuments(activeFilters: DocumentListFilters = filters) {
    try {
      setLoading(true);
      setErrorMessage("");

      const token = localStorage.getItem("adgs_access_token");

      if (!token) {
        throw new Error("Please login from the Dashboard page first.");
      }

      const data = await getDocuments(token, activeFilters);
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
    setFilters(DEFAULT_FILTERS);
    void loadDocuments(DEFAULT_FILTERS);
  }

  useEffect(() => {
    void loadDocuments(DEFAULT_FILTERS);
  }, []);

  return (
    <section className="page-section">
      <div className="hero-panel">
        <div>
          <h2>Governance Document Registry</h2>
          <p>
            Filter uploaded assets by approval status, risk score, conflict
            detection, and Qdrant Gold indexing state.
          </p>
        </div>

        <div className="system-pill">
          {loading ? "Loading..." : `${documents.length} Loaded`}
        </div>
      </div>

      <div className="filter-card">
        <div className="filter-grid">
          <div>
            <label>Status</label>
            <select
              value={filters.status}
              onChange={(event) => updateFilter("status", event.target.value)}
            >
              <option value="">All</option>
              <option value="UPLOADED">UPLOADED</option>
              <option value="PROCESSING">PROCESSING</option>
              <option value="PAUSED">PAUSED</option>
              <option value="WAITING_FOR_ADMIN">WAITING_FOR_ADMIN</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
              <option value="FAILED">FAILED</option>
            </select>
          </div>

          <div>
            <label>Category</label>
            <input
              value={filters.document_category}
              onChange={(event) =>
                updateFilter("document_category", event.target.value)
              }
              placeholder="Policy"
            />
          </div>

          <div>
            <label>Min Risk</label>
            <input
              type="number"
              min="0"
              max="100"
              value={filters.min_risk_score}
              onChange={(event) =>
                updateFilter("min_risk_score", event.target.value)
              }
              placeholder="75"
            />
          </div>

          <div>
            <label>Max Risk</label>
            <input
              type="number"
              min="0"
              max="100"
              value={filters.max_risk_score}
              onChange={(event) =>
                updateFilter("max_risk_score", event.target.value)
              }
              placeholder="100"
            />
          </div>

          <div>
            <label>Conflict</label>
            <select
              value={filters.conflict_found}
              onChange={(event) =>
                updateFilter("conflict_found", event.target.value)
              }
            >
              <option value="">All</option>
              <option value="true">Conflict Found</option>
              <option value="false">No Conflict</option>
            </select>
          </div>

          <div>
            <label>Indexed</label>
            <select
              value={filters.indexed}
              onChange={(event) => updateFilter("indexed", event.target.value)}
            >
              <option value="">All</option>
              <option value="true">Indexed</option>
              <option value="false">Not Indexed</option>
            </select>
          </div>

          <div>
            <label>Limit</label>
            <input
              type="number"
              min="1"
              max="100"
              value={filters.limit}
              onChange={(event) => updateFilter("limit", event.target.value)}
            />
          </div>

          <div>
            <label>Offset</label>
            <input
              type="number"
              min="0"
              value={filters.offset}
              onChange={(event) => updateFilter("offset", event.target.value)}
            />
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
                <th>Conflict</th>
                <th>Indexed</th>
                <th>Created</th>
              </tr>
            </thead>

            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="empty-state">
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
                        {document.conflict_found ? "Conflict" : "Clear"}
                      </span>
                    </td>

                    <td>
                      <span
                        className={booleanBadgeClass(
                          Boolean(document.qdrant_point_id),
                          "Indexed",
                        )}
                      >
                        {document.qdrant_point_id ? "Indexed" : "Not Indexed"}
                      </span>
                    </td>

                    <td>{formatDate(document.created_at)}</td>
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
