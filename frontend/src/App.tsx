import { useState } from "react";
import "./App.css";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";

type Page = "dashboard" | "documents";

function App() {
  const [page, setPage] = useState<Page>("dashboard");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-logo">A</div>
          <div>
            <h2>ADGS</h2>
            <p>Autonomous Governance</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button
            className={page === "dashboard" ? "sidebar-link active" : "sidebar-link"}
            onClick={() => setPage("dashboard")}
          >
            <span>Overview</span>
            <small>System audit summary</small>
          </button>

          <button
            className={page === "documents" ? "sidebar-link active" : "sidebar-link"}
            onClick={() => setPage("documents")}
          >
            <span>Documents</span>
            <small>Governance records</small>
          </button>
        </nav>

        <div className="sidebar-footer">
          <p>Governance MVP</p>
          <strong>Gold Collection Ready</strong>
        </div>
      </aside>

      <main className="main-content">
        <header className="top-header">
          <div>
            <p className="page-kicker">Enterprise AI Governance</p>
            <h1>
              {page === "dashboard" ? "Governance Dashboard" : "Document Governance"}
            </h1>
          </div>

          <div className="system-pill">
            <span className="pulse-dot" />
            Local Environment
          </div>
        </header>

        {page === "dashboard" ? <DashboardPage /> : <DocumentsPage />}
      </main>
    </div>
  );
}

export default App;
