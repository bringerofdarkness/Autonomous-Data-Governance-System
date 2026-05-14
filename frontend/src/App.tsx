import { useState } from "react";
import "./App.css";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentDetailPage } from "./pages/DocumentDetailPage";
import { DocumentsPage } from "./pages/DocumentsPage";

type Page = "dashboard" | "documents" | "document-detail";

function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null,
  );

  function openDocumentDetail(documentId: string) {
    setSelectedDocumentId(documentId);
    setPage("document-detail");
  }

  function backToDocuments() {
    setPage("documents");
  }

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
            className={
              page === "dashboard" ? "sidebar-link active" : "sidebar-link"
            }
            onClick={() => setPage("dashboard")}
          >
            <span>Overview</span>
            <small>System audit summary</small>
          </button>

          <button
            className={
              page === "documents" || page === "document-detail"
                ? "sidebar-link active"
                : "sidebar-link"
            }
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
              {page === "dashboard"
                ? "Governance Dashboard"
                : page === "documents"
                  ? "Document Governance"
                  : "Document Detail"}
            </h1>
          </div>

          <div className="system-pill">
            <span className="pulse-dot" />
            Local Environment
          </div>
        </header>

        {page === "dashboard" && <DashboardPage />}

        {page === "documents" && (
          <DocumentsPage onOpenDocument={openDocumentDetail} />
        )}

        {page === "document-detail" && selectedDocumentId && (
          <DocumentDetailPage
            documentId={selectedDocumentId}
            onBack={backToDocuments}
          />
        )}
      </main>
    </div>
  );
}

export default App;