import { useState } from "react";
import { executeRagSearch, type RagSearchResponse } from "../api/documentsApi";

export function RagSearchPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<RagSearchResponse | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      setError("");
      const token = localStorage.getItem("adgs_access_token");

      if (!token) {
        throw new Error("Authentication token missing. Please login from the Dashboard first.");
      }

      // Executes the query utilizing our clean apiRequest abstraction module
      const data = await executeRagSearch(token, query);
      setResults(data);
    } catch (err) {
      setResults(null);
      setError(err instanceof Error ? err.message : "An unexpected failure occurred during search.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-section">
      <div className="hero-panel">
        <div>
          <h2>Autonomous RAG Intelligence Hub</h2>
          <p>
            Query the verified corporate Gold Collection. All answers are strictly anchored to audited, 
            conflict-free context chunks with hallucination protection boundaries.
          </p>
        </div>
      </div>

      {/* SEARCH CONSOLE WRAPPER */}
      <div className="filter-card" style={{ marginBottom: "20px" }}>
        <form onSubmit={(e) => void handleSearch(e)} style={{ display: "flex", gap: "10px" }}>
          <input
            type="text"
            style={{ flex: 1, padding: "12px", borderRadius: "6px", border: "1px solid #ccc", fontSize: "15px" }}
            placeholder="Ask a compliance or data policy question... (e.g., What are the terms for Net-30?)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="primary-button" style={{ minWidth: "140px" }} disabled={loading}>
            {loading ? "Synthesizing..." : "Execute Query"}
          </button>
        </form>
        {error && <p className="error-message" style={{ marginTop: "10px" }}>{error}</p>}
      </div>

      {results && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", alignItems: "start" }}>
          
          {/* LEFT COLUMN: CONTEXT ANCHORED ANSWER */}
          <div className="table-card" style={{ padding: "20px", minHeight: "300px" }}>
            <div className="table-header" style={{ borderBottom: "1px solid #eee", paddingBottom: "10px", marginBottom: "15px" }}>
              <h3 style={{ margin: 0, color: "#1976d2" }}>🔒 Context-Anchored Synthesis</h3>
              <span className="status-badge status-approved" style={{ fontSize: "11px" }}>Deterministic Mode (Temp 0.0)</span>
            </div>
            <div style={{ fontSize: "15px", lineHeight: "1.6", color: "#333", backgroundColor: "#f9f9f9", padding: "15px", borderRadius: "6px", borderLeft: "4px solid #1976d2", whiteSpace: "pre-wrap" }}>
              {results.synthesized_answer || "No synthesized output returned from target provider."}
            </div>
            <p style={{ fontSize: "12px", color: "#666", marginTop: "15px", fontStyle: "italic" }}>
              * Statements are mapped dynamically to underlying Qdrant data vectors using source markers.
            </p>
          </div>

          {/* RIGHT COLUMN: RELEVANT ATTRIBUTION CHUNKS */}
          <div className="table-card" style={{ padding: "20px", minHeight: "300px" }}>
            <div className="table-header" style={{ borderBottom: "1px solid #eee", paddingBottom: "10px", marginBottom: "15px" }}>
              <h3 style={{ margin: 0, color: "#2e7d32" }}>📄 Audited Qdrant Attributions</h3>
              <span className="system-pill">{results.matches.length} Segments Retrieved</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxHeight: "450px", overflowY: "auto", paddingRight: "5px" }}>
              {results.matches.length === 0 ? (
                <p style={{ color: "#777", textAlign: "center", marginTop: "40px" }}>No reference chunks cleared the minimum confidence threshold.</p>
              ) : (
                results.matches.map((match, idx) => (
                  <div key={match.point_id || idx} style={{ border: "1px solid #e0e0e0", borderRadius: "6px", padding: "12px", backgroundColor: "#fff" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "12px" }}>
                      <strong style={{ color: "#555" }}>[Source ID: {idx + 1}] Doc ID: {String(match.metadata?.document_id || "Unknown").substring(0, 8)}...</strong>
                      <span className="risk-badge risk-low" style={{ backgroundColor: "#e8f5e9", color: "#2e7d32", padding: "2px 6px", borderRadius: "4px" }}>
                        Match Score: {(match.score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: "13px", color: "#444", lineHeight: "1.4", fontFamily: "monospace" }}>
                      "{match.text}"
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      )}
    </section>
  );
}