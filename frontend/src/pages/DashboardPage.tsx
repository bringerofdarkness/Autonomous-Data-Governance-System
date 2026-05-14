import { useState } from "react";
import { login } from "../api/authApi";
import {
  getSystemAuditSummary,
  type SystemAuditSummary,
} from "../api/systemApi";

function StatCard({
  title,
  value,
}: {
  title: string;
  value: number | string;
}) {
  return (
    <div className="stat-card">
      <p>{title}</p>
      <h2>{value}</h2>
    </div>
  );
}

export function DashboardPage() {
  const [username, setUsername] = useState("admin@adgs.com");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("adgs_access_token") || "");
  const [summary, setSummary] = useState<SystemAuditSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadDashboard() {
    try {
      setLoading(true);
      setErrorMessage("");

      let activeToken = token;

      if (!activeToken) {
        const loginResponse = await login(username, password);
        activeToken = loginResponse.access_token;
        setToken(activeToken);
        localStorage.setItem("adgs_access_token", activeToken);
      }

      const data = await getSystemAuditSummary(activeToken);
      setSummary(data);
    } catch (error) {
      setSummary(null);
      setErrorMessage(
        error instanceof Error ? error.message : "Could not load dashboard.",
      );
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("adgs_access_token");
    setToken("");
    setSummary(null);
    setPassword("");
  }

  return (
    <section className="page-section">
      <div className="hero-panel">
        <div>
          <h2>Policy Intelligence Control Room</h2>
          <p>
            A live operational view of sensitive document intake, risk scoring,
            human approval decisions, Gold Collection indexing, and retrieval
            audit activity.
          </p>
        </div>

        <div className="system-pill">
          <span className="pulse-dot" />
          Governance Active
        </div>
      </div>

      <div className="card-panel">
        {!token ? (
          <div className="login-grid">
            <div className="form-control">
              <label>Admin Email</label>
              <input
                type="email"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="admin@adgs.com"
              />
            </div>

            <div className="form-control">
              <label>Admin Password</label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter admin password"
              />
            </div>

            <button
              className="primary-button"
              onClick={loadDashboard}
              disabled={loading || !username.trim() || !password.trim()}
            >
              {loading ? "Loading..." : "Sign in"}
            </button>
          </div>
        ) : (
          <div className="button-row">
            <button className="primary-button" onClick={loadDashboard} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh Metrics"}
            </button>

            <button className="secondary-button" onClick={logout}>
              Sign out
            </button>
          </div>
        )}

        {errorMessage && <p className="error-message">{errorMessage}</p>}
      </div>

      {summary && (
        <>
          <div className="stats-grid">
            <StatCard title="Total Documents" value={summary.documents.total} />
            <StatCard title="Approved" value={summary.documents.approved} />
            <StatCard title="Paused" value={summary.documents.paused} />
            <StatCard title="Gold Indexed" value={summary.documents.indexed} />
            <StatCard title="High Risk" value={summary.documents.high_risk} />
            <StatCard title="Conflicts" value={summary.documents.conflict_found} />
            <StatCard title="RAG Searches" value={summary.rag.total_searches} />
            <StatCard title="Audit Events" value={summary.audit_logs.document_audit_logs_total} />
          </div>

          <p className="generated-at">
            Metrics generated {new Date(summary.generated_at).toLocaleString()}
          </p>
        </>
      )}
    </section>
  );
}
