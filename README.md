# Autonomous Data Governance System (ADGS) v2.0
An enterprise-grade, asynchronous security firewall and compliance gatekeeper for Retrieval-Augmented Generation (RAG) pipelines.

---

## Executive Summary

Most Retrieval-Augmented Generation (RAG) architectures follow a naive ingestion pattern: **Upload File ➔ Chunk ➔ Embed ➔ Index into Vector Store**. While this works for early prototypes, it introduces critical vulnerabilities in production. Standard ingestion pipelines lack validation, leading to the exposure of Personally Identifiable Information (PII), index contamination with outdated policies, and the ingestion of conflicting corporate data. Once contaminated knowledge enters the vector space, downstream LLMs inherit these risks, producing non-compliant or inaccurate responses.

The **Autonomous Data Governance System (ADGS)** is a production-grade governance middleware designed to sit *before* the vector database. It intercepts, audits, sanitizes, and validates multi-format document intakes within a distributed asynchronous architecture. Powered by a stateful **LangGraph** workflow and backed by a **Celery/Redis** task queue, ADGS runs documents through multi-layer verification (PII redaction, semantic conflict auditing, risk scoring) and enforces a **Human-in-the-Loop (HITL)** approval gate before any chunk is permitted into the trusted vector store.

---

## 1. Why ADGS? (The Value Proposition)

In modern enterprise architectures, AI-ready data must be treated with the same validation rigor as traditional database writes. ADGS provides the necessary security and compliance infrastructure to enforce these boundaries:

* **Preventing Data Leaks in RAG Contexts:** If an employee uploads a document containing confidential files (e.g., payroll data, social security numbers, API keys), ADGS's PII scrubber automatically redacts it before vectorization, neutralizing the risk of downstream leakages through semantic search.
* **Neutralizing Document Contradictions:** If an outdated corporate policy is uploaded (e.g., stating a "30-day refund window" when the current policy is "14 days"), the Conflict Agent detects the semantic overlap and alerts administrators to prevent LLM hallucination and policy confusion.
* **Enforcing compliance boundaries:** Rather than relying on soft prompts to tell the LLM "do not read sensitive data," ADGS secures the data at the ingestion level. Unapproved or high-risk files are physically isolated from the vector index.

---

## 2. System Beneficiaries

* **Compliance Officers & Data Auditors:** Receive a centralized, immutable, and database-backed audit log of every document state change, user action, and sanitization step, ensuring full auditable accountability.
* **Security Engineers:** Can define and enforce risk thresholds, blocking raw or unscrubbed PII from ever crossing the boundary into public vector namespaces.
* **AI Developers & Architects:** Gain a trusted, clean "Gold Collection" vector index. Downstream RAG agents can query the index with high confidence, knowing the context chunks are pre-scrubbed, factually validated, and clean.
* **Enterprise Decision Makers:** Can safely roll out internal AI chatbots to thousands of employees without fear of horizontal privilege escalation or intellectual property leaks.

---

## 3. Pre-Build Design Philosophy

Before writing the first line of code, the system was designed around three architectural constraints:

1. **AI Ingest is an Untrusted Write Operation:** In classic web development, we never run raw SQL queries from client input without sanitizing them. We must treat document uploads for AI ingestion with the same suspicion. Every file must pass through a strict semantic and structural sanitization pipeline.
2. **Heavy Computations Must Be Decoupled:** Parsing large documents, running local transformer embeddings, searching vectors, and invoking LLMs are computationally heavy operations. Running these synchronously on the web-request thread blocks the server. The architecture had to run asynchronously using background workers.
3. **State Integrity Across Interruptions:** Because human approval is required for high-risk files, the system needed a way to pause mid-workflow, serialize its execution memory, and resume cleanly without losing context or restarting the pipeline.

---

## 4. Project Planning & Phases

The system was developed in structured phases to transition from a lightweight proof-of-concept to a production-grade backend:

* **Phase 1: FastAPI Prototype (v1.0):** Established the core ingestion endpoints, local PostgreSQL tables via SQLAlchemy Async, and a basic synchronous pipeline using regex scrubbers and a local Qdrant container.
* **Phase 2: Transition to Django and DRF (v2.0):** Overhauled the API gateway to Django REST Framework (DRF) to utilize Django's stable database ORM, robust transaction controls, and built-in Admin Panel for human review.
* **Phase 3: Background Worker Offloading:** Integrated Celery with Redis as the broker to handle document parsing and AI workloads asynchronously, ensuring the API gateway remains highly responsive.
* **Phase 4: Stateful Graph Orchestration:** Replaced sequential execution scripts with a cyclical state machine using LangGraph. Configured a PostgreSQL checkpointer (`PostgresSaver`) to handle thread serialization and Human-in-the-Loop (HITL) execution pauses.
* **Phase 5: Advanced Document Ingest & RAG Integration:** Implemented format-specific extraction adapters (handling PDFs, DOCX tables, Excel flattening, and recursive JSON parsing) and integrated cloud-based Google Gemini endpoints with exponential-backoff retries.

---

## 5. Technology Stack

| Domain | Technology | Implementation Detail |
| :--- | :--- | :--- |
| **API Gateway Framework** | Django + DRF | Exposes REST endpoints, handles database transactions, and manages RBAC. |
| **Workflow Orchestration** | LangGraph | Cycles documents through validation nodes; handles state serialization. |
| **State Checkpointing** | `PostgresSaver` | Serializes active LangGraph memory into PostgreSQL tables. |
| **Background Task Queue** | Celery + Redis | Offloads heavy document analysis and vectorization from the main thread. |
| **Relational Database** | PostgreSQL | Stores relational document metadata, audit logs, and system users. |
| **Vector Database** | Qdrant | Stashes chunk-level embeddings in a protected "Gold Collection" namespace. |
| **Embedding Generation** | `SentenceTransformer` | Local `all-MiniLM-L6-v2` model generating dense 384-dimensional vectors. |
| **LLM Synthesis Provider** | Google Gemini API | Uses `gemini-2.5-flash` for factual RAG synthesis with retry logic. |
| **Frontend Dashboard** | React + Vite + TS | Renders real-time governance metrics, file registries, and RAG UI. |
| **Containerization** | Docker Compose | Local orchestration for PostgreSQL, Redis, and Qdrant database servers. |

---

## 6. What's Enhanced in v2.0 (Over the v1.0 Prototype)

The v2.0 architecture represents a complete migration designed to solve the scaling and operational bottlenecks of the original v1.0 prototype:

* **Built-in Administrative Tooling:** Added the **Django Admin Panel**, serving as a full-featured admin command center. Administrators can filter files by risk, inspect detected PII, review semantic conflict details, and trigger manual vector index repairs.
* **Cyclical Stateful Workflows (LangGraph):** Replaced linear processing scripts with a stateful Graph. High-risk uploads (PII found or conflict detected) trigger an automatic pause, saving the graph state in Postgres, and waiting for an admin `APPROVE` or `REJECT` callback to resume.
* **Asynchronous Offloading (Celery + Redis):** Document extraction, PII scrubbing, conflict scanning, and vector indexing are offloaded to background Celery workers. The REST API returns immediate receipts, maintaining 100% gateway uptime.
* **Robust Password Compatibility:** Implemented a custom auth backend (`ADGSAuthBackend`) allowing Django to securely verify legacy passwords hashed with FastAPI’s `pwdlib` (`argon2`/`bcrypt`) alongside Django's standard hashing algorithms.
* **Dynamic Multi-Format Adapters:** Built deep parser support for 6 formats: table structure extraction in `.docx`, sheet relational flattening in `.xlsx`, recursive path mapping for nested `.json` trees, alongside `.pdf`, `.csv`, and `.txt`.
* **Resilient Cloud LLM Integration:** Migrated the RAG synthesis engine from local Ollama to cloud-based Google Gemini. Added an exponential-backoff retry layer to survive transient 503 rate-limits or network spikes.

---

## 7. Project Architecture & System Design

### System Design Story (Data Lifecycle)
1. **Ingest:** A user uploads a document through the React Frontend. The API Gateway (Django REST Framework) saves the file locally in `storage/uploads/`, registers its metadata as `UPLOADED` in PostgreSQL, and queues `process_document_task` to Celery via Redis.
2. **Worker Handoff & Graph Launch:** A background Celery worker picks up the task and compiles a stateful **LangGraph** instance configured with a database-backed `thread_id` (`document:{uuid}`).
3. **Extraction Node (`text_loader`):** Extracts raw text. For relational formats (`.xlsx`, `.csv`), it flattens the rows to preserve structure. For nested `.json`, it flattens paths.
4. **Classification Node (`categorizer`):** Inspects the text to determine the category (HR, Finance, Legal, etc.).
5. **PII Sanitizer Node (`pii_scrubber`):** Scans the text using regex and semantic patterns for emails, phone numbers, and custom IDs. It produces a redacted text file saved to `storage/cleaned/`.
6. **Conflict Auditor Node (`conflict_agent`):** Queries Qdrant using embeddings generated via local `SentenceTransformers` to search for semantic overlaps. If it finds conflicting facts, it flags the state as `conflict_found=True` and drafts a conflict summary.
7. **Critic Evaluation (`critic`):** Computes a composite risk score based on category sensitivity, PII counts, and semantic conflicts. 
   * **Low Risk:** Bypasses human review and transitions directly to indexing.
   * **High Risk:** Sets `requires_admin_approval=True`, pausing graph execution. The active state is serialized into PostgreSQL by the `PostgresSaver`.
8. **Human-in-the-Loop Gate:** The document status is updated to `PAUSED` in PostgreSQL. An admin reviews the document details on the Django Admin panel or React dashboard.
   * **If Rejected:** The admin clicks `Reject`. The workflow terminates, and the document is marked `REJECTED`.
   * **If Approved:** The admin clicks `Approve`. The system sends a resume request to the backend. The graph is reloaded from the PostgreSQL checkpoint and proceeds past the pause state.
9. **Vector Indexing:** The cleaned text is chunked, converted to dense vector embeddings, and upserted into Qdrant's `adgs_gold_documents` collection. The document is marked `APPROVED`.
10. **Querying (Secure RAG):** Users ask questions in the RAG UI. The system queries Qdrant to pull relevant chunks *only* from the approved list of documents, feeds the chunks to the Gemini API, and returns fact-anchored answers.

### Architecture Diagram

```mermaid
flowchart TD
    %% Clients
    User[React Ingestion & Chat Client] <-->|HTTP/REST APIs| DjangoGateway[Django REST Framework Gateway]
    Admin[Django Admin Command Center] <-->|Inspect & Approve| DjangoGateway

    %% Gateway & Queue
    DjangoGateway <-->|Read/Write Metadata & Audit Logs| PostgresDB[(PostgreSQL Database)]
    DjangoGateway -->|Enqueue Tasks| RedisBroker[Redis Task Broker]

    %% Background Workers
    RedisBroker -->|Dequeue| CeleryWorker[Celery Asynchronous Worker]

    %% Stateful Graph Workflow
    subgraph Celery Task Container
        CeleryWorker -->|Compiles & Invokes| LangGraph[LangGraph State Machine]
        
        LangGraph -->|1. Extract| NodeExtract[text_loader_node]
        LangGraph -->|2. Categorize| NodeCat[categorizer_node]
        LangGraph -->|3. Scrub PII| NodeScrub[pii_scrubber_node]
        LangGraph -->|4. Conflict Scan| NodeConflict[conflict_agent_node]
        LangGraph -->|5. Evaluate Risk| NodeCritic[critic_node]
        
        %% Checkpoint persistence
        LangGraph <-->|Save/Load Execution Snapshots| PostgresCheckpointer[(PostgresSaver Checkpoints)]
        
        %% Conditional routing
        NodeCritic -->|High Risk Flag| NodeHITL[hitl_review_node]
        NodeCritic -->|Low Risk Flag| NodeAutoIndex[Auto-Approve Gate]
        
        NodeHITL -->|Interrupts Execution| PausedState[PAUSED Status in DB]
    end

    %% Human-in-the-loop action
    Admin -.->|Approve/Resume Callback| DjangoGateway
    DjangoGateway -->|Send Command to Graph| LangGraph
    
    %% Output layers
    LangGraph -->|Approved Document Indexing| IndexService[Document Indexing Service]
    IndexService -->|Generate Embeddings| LocalModel[SentenceTransformer]
    LocalModel -->|Upsert Chunks| QdrantDB[(Qdrant Vector DB)]

    %% Secure Retrieval
    DjangoGateway -->|Semantic Query| QdrantDB
    DjangoGateway <-->|Context-Anchored Synthesis| GeminiAPI[Google Gemini Cloud API]
```

---

## 8. Local Development Setup

To run ADGS locally, follow these steps to configure your environment, start the infrastructure databases, migrate schemas, and run the backend servers.

### Prerequisites
* **Python 3.10+** installed on your system.
* **Node.js (v18+)** and **npm** installed.
* **Docker Desktop** installed and running.
* A valid **Google Gemini API Key**.

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/bringerofdarkness/Autonomous-Data-Governance-System.git
cd Autonomous-Data-Governance-System
```

---

### Step 2: Configure Environment Variables
Create a `.env` file in the project root folder. Copy the configuration below:

```env
PROJECT_NAME="ADGS - Autonomous Data Governance System"
ENVIRONMENT=local

# Initial Admin Seeding Configuration
FIRST_ADMIN_EMAIL=admin@adgs.com
FIRST_ADMIN_PASSWORD=Admin@12345

# Database Configurations
POSTGRES_USER=adgs_user
POSTGRES_PASSWORD=adgs_password
POSTGRES_DB=adgs_db
POSTGRES_HOST=localhost
POSTGRES_PORT=15432
DATABASE_URL=postgresql://adgs_user:adgs_password@localhost:15432/adgs_db
LANGGRAPH_CHECKPOINT_DATABASE_URL=postgresql://adgs_user:adgs_password@localhost:15432/adgs_db

# Message Broker Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0

# Vector Database Configuration
QDRANT_HOST=localhost
QDRANT_PORT=16333
QDRANT_URL=http://localhost:16333
QDRANT_GOLD_COLLECTION=adgs_gold_documents
QDRANT_VECTOR_SIZE=384

# Authentication Settings
JWT_SECRET_KEY=change-this-local-secret-key-to-something-secure
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM Providers Configuration
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=llama3
```

---

### Step 3: Run Infrastructure Databases (Docker)
Start PostgreSQL, Redis, and Qdrant containers in background mode using the configured `docker-compose.yml`:

```bash
docker compose up -d
```

Verify that all three database servers are running:
```bash
docker compose ps
```
* **PostgreSQL** runs on port `15432`
* **Redis** runs on port `6379`
* **Qdrant** runs on port `16333` (Dashboard accessible at [http://localhost:16333/dashboard](http://localhost:16333/dashboard))

---

### Step 4: Install Backend Dependencies
Create a virtual environment, activate it, and install the required dependencies:

#### Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Step 5: Run Django Migrations & Seed Default Data
Apply database migrations to structure PostgreSQL tables and set up the LangGraph checkpointer storage:

```bash
# Apply Django migrations
python manage.py migrate

# Initialize LangGraph Checkpoints (if required manually)
python -m app.db.setup_langgraph_checkpoints
```

To create your superuser account for logging in, run the Django command:
```bash
python manage.py createsuperuser
```
Provide the email and password you configured in your `.env` file (e.g., `admin@adgs.com` / `Admin@12345`).

---

### Step 6: Start Runtime Services
To run the entire system, you will need to open three terminal windows:

#### Terminal 1: Django REST Gateway
Start the backend Django API web server:
```bash
# Ensure virtualenv is active
python -m uvicorn django_project.asgi:application --reload --port 8080
```

#### Terminal 2: Celery Background Worker
Start the Celery worker to handle document processing queues:
```bash
# Ensure virtualenv is active
celery -A django_project worker --loglevel=info --pool=solo
```

#### Terminal 3: React Frontend Dashboard
Navigate to the frontend folder, install dependencies, and start the Vite dev server:
```bash
cd frontend
npm install
npm run dev
```
The React UI will run on [http://localhost:5173/](http://localhost:5173/) or [http://localhost:5174/](http://localhost:5174/).

---

## 9. Testing & Quality Assurance
The codebase includes a comprehensive test suite covering API contracts, PII detection logic, and task-queue handoffs. Run tests using `pytest`:

```bash
pytest tests/ -v -s
```

---

## 10. Summary of Key Files

* [django_project/settings.py](file:///F:/Self%20Project/ADGS-%20Autonomous%20Data%20Governance%20System/django_project/settings.py) - Central Django app settings, middlewares, CORS, database routing, and Celery configuration.
* [app/models.py](file:///F:/Self%20Project/ADGS-%20Autonomous%20Data%20Governance%20System/app/models.py) - Relational DB schema for users, documents, and audit registries.
* [app/views.py](file:///F:/Self%20Project/ADGS-%20Autonomous%20Data%20Governance%20System/app/views.py) - API controllers processing RAG queries, document approvals, and auth flows.
* [app/tasks.py](file:///F:/Self%20Project/ADGS-%20Autonomous%20Data%20Governance%20System/app/tasks.py) - Celery tasks orchestrating the background LangGraph invocations.
* [app/graph/workflow.py](file:///F:/Self%20Project/ADGS-%20Autonomous%20Data%20Governance%20System/app/graph/workflow.py) - High-level graph topology mapping validation nodes.
* [app/services/document_extraction_service.py](file:///F:/Self%20Project/ADGS-%20Autonomous%20Data%20Governance%20System/app/services/document_extraction_service.py) - Multi-format loaders transforming inputs into raw text.
* [app/services/llm_service.py](file:///F:/Self%20Project/ADGS-%20Autonomous%20Data%20Governance%20System/app/services/llm_service.py) - Resilient Gemini generation engine with backoff-retry handlers.