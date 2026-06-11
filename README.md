# Autonomous Data Governance System (ADGS) v2.0
A production-grade, asynchronous semantic firewall and compliance gatekeeper for Retrieval-Augmented Generation (RAG) pipelines.

---

## 1. Why ADGS? (The Core Problem & Value Proposition)

Retrieval-Augmented Generation (RAG) is the industry standard for grounding LLMs in corporate data. However, the naive implementation of RAG introduces severe compliance, privacy, and accuracy risks:

```text
User Upload ➔ Naive Ingestion ➔ Vector Database ➔ Downstream LLM (Exposes Sensitive Data)
```

Without an intermediate governance layer, organizations risk indexing confidential files directly into shared vector stores. Once contaminated knowledge enters the vector space, it is near-impossible to prevent downstream LLMs from retrieving and exposing it to unauthorized users.

**ADGS solves this** by acting as an intelligent security gatekeeper sitting between raw document ingestion and your vector database. It inspects, sanitizes, audits, and validates all document content *before* it gets vectorized and stored.

---

## 2. System Scenarios: Before vs. After ADGS

### Scenario: The Customer Service Chatbot Contamination
A company integrates an internal AI chatbot to help agents retrieve support policies. An employee accidentally uploads an Excel sheet containing customer names, credit card details, and social security numbers, alongside an outdated corporate policy stating: *"Refunds are valid up to 45 days"* (the current policy only allows 14 days).

#### ❌ WITHOUT ADGS (The Vulnerability)
1. The spreadsheet is parsed and directly embedded into the vector database.
2. A customer support agent asks: *"What is our refund window?"*
3. The LLM retrieves the outdated refund window (45 days) and hallucinated guidelines, leading to financial leakage.
4. A malicious employee queries: *"Show me the details of customer John Doe."*
5. The LLM retrieves and outputs the customer's social security number and credit card details directly from the vector store.
6. **Result:** Compliance violations (GDPR/HIPAA/PCI-DSS), data leakage, and customer trust breakdown.

####  WITH ADGS (The Solution)
1. The employee uploads the spreadsheet. ADGS immediately intercepts it.
2. **PII Sanitizer:** The system automatically scans the document, redacting all names, credit cards, and SSNs.
3. **Conflict Agent:** The system generates embeddings of the document segments, runs a semantic similarity lookup in Qdrant, and flags that the "45-day refund policy" contradicts the existing approved "14-day refund policy."
4. **Critic Node:** Because conflicts and PII are detected, the system calculates a high risk score, halts the pipeline, and serializes the workflow state into PostgreSQL.
5. **Human-in-the-Loop (HITL):** The document goes into a `PAUSED` state. The compliance team receives an alert on the admin dashboard, reviews the flagged contradictions and redacted PII, and clicks **REJECT**.
6. **Result:** The vector database remains clean, secure, and compliant. The dangerous data is blocked at the gate.

---

## 3. Key Benefits

* **PII Leakage Prevention:** Automatically sanitizes sensitive identifiers (emails, phone numbers, SSNs, credit cards) before they are stored in the vector database.
* **Semantic Integrity & Accuracy:** Scans new documents for contradictions against the existing knowledge base, preventing LLM hallucinations caused by conflicting information.
* **Human-in-the-Loop Oversight:** Pauses high-risk workflows for administrator review, giving compliance teams ultimate control over what data the AI is trained on.
* **Asynchronous Web Scalability:** Offloads heavy processing workloads to background queues, keeping the web API fast and highly responsive.
* **Immutability of Audit Trails:** Tracks every document's lifecycle through detailed relational logs, facilitating security audits and SOC2 compliance.

---

## 4. Supported Formats & Extraction Strategies

ADGS doesn't treat documents as flat text strings. It employs format-specific parsing strategies to maintain semantic integrity:

| Format | Parsing Engine | Ingestion Strategy | Use Case |
| :--- | :--- | :--- | :--- |
| **`.pdf`** | `pypdf` | Page-by-page text extraction, OCR-ready empty layer checks. | Manuals, agreements, policy files. |
| **`.docx`** | `python-docx` | Relational table extraction and paragraph structural mapping. | Legal contracts, proposals. |
| **`.xlsx`** | `openpyxl` | Row-by-row relational serialization and sheet flattening. | Financial worksheets, reports. |
| **`.csv`** | Python built-in | Relational record flattening (e.g., `Row 12 - Name: X, ID: Y`). | Structured user lists, system logs. |
| **`.json`** | Python built-in | Recursive key-path flattening (e.g., `user.auth.role = Admin`). | Configuration files, structured API data. |
| **`.txt`** | Python built-in | Raw text segment reading. | Plain logs, readmes, text notes. |

---

## 5. Target Users & Stakeholders

* **AI Engineers & Architects:** Developers looking for a secure, audited vector ingestion pipeline to keep their RAG chatbots accurate and hallucination-free.
* **Information Security Officers (CISOs):** Compliance leads who need to prevent data leakage and ensure GDPR, HIPAA, or PCI-DSS requirements are met in corporate LLM applications.
* **Document Registrars & Admins:** Operators who upload, categorize, review, and approve corporate knowledge bases on a day-to-day basis.

---

## 6. How I Thought About & Planned the System

### Pre-Building Ideation (The Design Philosophy)
Before coding the project, I established a set of core principles:
1. **AI Ingest is a Database Write:** Just as we validate user schemas and sanitize SQL inputs in a REST API, we must validate semantic meaning and sanitize PII in AI data pipelines. Ingest must be separate from retrieval.
2. **State Isolation:** A vector database is production infrastructure. It should only store "Gold Standard" knowledge. Data in intermediate states must be isolated.
3. **State Persistence & Re-entry:** A human review process requires workflows to pause and wait. To scale this, the workflow state must be serialized to a physical database (PostgreSQL) and re-instantiated upon administrator approval.

### Project Planning Roadmap
* **V1 Prototype (FastAPI):** Built a lightweight, async API using FastAPI, SQLAlchemy Async, and a basic regex PII scrubber. Focus was on building the extraction and vector lookup mechanics.
* **V2 Production Migration (Django + LangGraph + Celery):** Migrated to Django and DRF to gain stable ORM transactions, secure migrations, and a ready-made administrative interface (Django Admin). Integrated Celery for queue offloading, and rebuilt the pipeline using a cyclical state machine in LangGraph to handle human-in-the-loop checkpoints.

---

## 7. Technology Stack

* **Backend Gateway:** Django REST Framework (DRF) — handles request parsing, authentication, and database writes.
* **Workflow Orchestrator:** LangGraph — manages cyclical pipelines, nodes, conditional edges, and state serialization.
* **State Checkpointer:** `PostgresSaver` — persists the active state of LangGraph threads directly into PostgreSQL.
* **Background Worker Queue:** Celery + Redis — processes document loading, scrubbing, vector embedding, and LLM calls.
* **Vector Store:** Qdrant — houses vector embeddings in the `adgs_gold_documents` namespace.
* **Local Embeddings:** SentenceTransformers (`all-MiniLM-L6-v2`) — generates dense 384-dimensional vector representations locally.
* **Cloud LLM synthesis:** Google Gemini API (`gemini-2.5-flash`) — powers secure RAG query answering.
* **Frontend Dashboard:** React (TypeScript) + Vite — interface for document uploads, registries, and chat retrieval.

---

## 8. System Architecture Diagram

```mermaid
flowchart TD
    %% Client Interfaces
    User[React Ingestion & Chat Client] <-->|API Calls| DjangoAPI[Django REST Framework Gateway]
    Admin[Django Admin Console] <-->|Review & Approve| DjangoAPI

    %% Database & Queue
    DjangoAPI <-->|Write Metadata & Logs| PostgresDB[(PostgreSQL DB)]
    DjangoAPI -->|Enqueue Task| RedisBroker[Redis Task Queue]

    %% Asynchronous Worker Container
    RedisBroker -->|Dequeue| CeleryWorker[Celery Asynchronous Worker]
    
    subgraph Celery Worker Environment
        CeleryWorker -->|Compiles & Invokes| LangGraph[LangGraph State Machine]
        
        LangGraph -->|1. Load Text| NodeLoader[text_loader_node]
        LangGraph -->|2. Categorize| NodeCat[categorizer_node]
        LangGraph -->|3. Scrub PII| NodeScrub[pii_scrubber_node]
        LangGraph -->|4. Audit Conflicts| NodeConflict[conflict_agent_node]
        LangGraph -->|5. Evaluate Risk| NodeCritic[critic_node]
        
        LangGraph <-->|State Snapshot| PostgresCheckpointer[(PostgresSaver Checkpoints)]
        
        NodeCritic -->|High Risk Flag| NodeHITL[hitl_review_node]
        NodeCritic -->|Low Risk Flag| NodeAutoIndex[Auto-Approve Gate]
        
        NodeHITL -->|Pauses Graph| PausedDB[PAUSED Status in Postgres]
    end

    %% Resume Action
    Admin -.->|Approve Callback| DjangoAPI
    DjangoAPI -->|Resume Graph Command| LangGraph
    
    %% Output
    LangGraph -->|Approved Vectorization| Indexer[Document Indexing Service]
    Indexer -->|Generate Dense Embeddings| LocalTransformer[SentenceTransformer]
    LocalTransformer -->|Upsert Chunks| QdrantDB[(Qdrant Vector DB)]

    %% Secure Retrieval
    DjangoAPI -->|Semantic Search| QdrantDB
    DjangoAPI <-->|Context-Anchored Synthesis| GeminiAPI[Google Gemini API]
```

---

## 9. Codebase Map & File Responsibilities

Below is a map of the important files in the repository and what they do:

```text
├── django_project/
│   ├── settings.py          # Central Django configuration (CORS, Middlewares, DB routing, Celery integration)
│   ├── celery.py            # Celery application instantiation and broker URL configuration
│   └── urls.py              # Root routing table mapping backend API pathways
│
├── app/
│   ├── models.py            # Relational database models (User, Role, DocumentMetadata, Audit Logs)
│   ├── admin.py             # Custom Django Admin panel logic (Approval actions, risk badges, status filters)
│   ├── views.py             # DRF ViewSets for uploads, resume requests, RAG search, and audit registry
│   ├── serializers.py       # Serializers translating database objects to Vite-compatible JSON
│   ├── tasks.py             # Celery background tasks running the LangGraph state machine
│   │
│   ├── graph/               # LangGraph Workflow Orchestration
│   │   ├── workflow.py      # Core graph definition, node registry, and conditional routing rules
│   │   ├── nodes.py         # Node implementations (parsing text, categorizing, scrubbing, conflict scanning)
│   │   ├── state.py         # Typing configuration for the cyclical graph's shared memory state
│   │   └── checkpoint.py    # PostgresSaver connection manager for workflow checkpointing
│   │
│   └── services/            # Isolated business-logic layer
│       ├── document_extraction_service.py   # Multi-format loaders (PDF, DOCX, CSV relational flattener)
│       ├── pii_scrubber_service.py          # Regex and pattern-based PII scrubber
│       ├── conflict_service.py              # Queries Qdrant to find conflicting semantic overlaps
│       ├── llm_service.py                   # Google Gemini connector with backoff retry loop
│       └── qdrant_service.py                # Qdrant client connection setup and collection manager
```

---

## 10. Most Challenging Parts (The Engineering Hurdles)

### 1. LangGraph Checkpointing in a Distributed Celery Context
**The Challenge:** LangGraph's human-in-the-loop pause requires serializing the execution state into a database. When running inside Celery background tasks, managing database connections across separate worker processes is tricky.
**The Solution:** I implemented the `PostgresSaver` checkpointer using a raw `psycopg` connection, passing it to the graph compilation stage. When the Critic Node pauses, the state is safely saved in PostgreSQL. Once an admin hits `/resume`, a new Celery task is spawned, loads the thread ID from the DB checkpointer, and picks up exactly where the workflow left off.

### 2. Semantic Contradiction Mapping (Conflict Agent)
**The Challenge:** Determining if a document contradicts existing information without causing false positives. For example, updating a phone number is an update, not necessarily a dangerous contradiction, but changing a legal policy is.
**The Solution:** The Conflict Agent generates dense vectors of the new text chunks, queries Qdrant to pull the top 3 semantically closest chunks, and feeds both texts to the Gemini LLM with a specialized system prompt. The model evaluates whether the differences constitute a logical contradiction, flagging them for human review.

### 3. Preserving Layout Meaning in Structural Formats (CSV/JSON/Excel)
**The Challenge:** Vector databases require text chunks. Pushing raw CSV lines (`John,Doe,34,Admin`) causes the embedding model to lose the connection between values and headers.
**The Solution:** I built custom parser adapters. CSV/Excel sheets are flattened relationally (e.g., `Row 12 - Name: John Doe, Age: 34, Role: Admin`), while nested JSONs are converted into fully qualified path strings. This keeps the semantic context clean for the vectorizer.

---

## 11. Learnings & Key Takeaways

* **Decoupling is Crucial for AI Pipelines:** AI workloads are heavy and slow. Wrapping everything in synchronous API calls causes timeouts and server crashes. Background queueing via Celery is essential for any production-grade AI system.
* **Input Sanitization Applies to AI:** We must treat unstructured text inputs with the same validation mindset as structured JSON inputs. Protecting the vector store is the only way to build secure corporate RAG systems.
* **State Machines Ease Complex Workflows:** Managing multistage pipelines (Extract ➔ Categorize ➔ Scrub ➔ Audit ➔ Review ➔ Index) with raw Python code becomes a spaghetti mess. Using a graph-based state machine (LangGraph) makes the execution deterministic, structured, and easy to modify.

---

## 12. Visualizations & Interface Showcases

*Here is a preview of the ADGS Enterprise Administration Dashboard. You can replace these placeholders with your active screenshots/recordings.*

### 1. Operational Ingestion Dashboard
The dashboard monitoring incoming file streams, processing logs, and safety flags.

*`[Screenshot Placeholder: dashboard_overview.png]`*

### 2. Document Audit & Approval Registry
The centralized command room where admins inspect detected PII and review semantic contradictions.

*`[Screenshot Placeholder: document_registry.png]`*

### 3. Secured RAG Interface
The interface where users interact with the approved and audited knowledge base.

*`[Screenshot Placeholder: rag_chat.png]`*

---

## 13. Local Development Setup

To run ADGS locally, follow these steps to configure your environment, start the databases, apply migrations, and spin up the backend and frontend servers.

### Prerequisites
* **Python 3.10+**
* **Node.js (v18+)** and **npm**
* **Docker Desktop**
* A valid **Google Gemini API Key**

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/bringerofdarkness/Autonomous-Data-Governance-System.git
cd Autonomous-Data-Governance-System
```

---

### Step 2: Configure Environment Variables
Create a `.env` file in the project root folder:

```env
PROJECT_NAME="ADGS - Autonomous Data Governance System"
ENVIRONMENT=local

# First Admin Configuration
FIRST_ADMIN_EMAIL=admin@adgs.com
FIRST_ADMIN_PASSWORD=Admin@12345

# Database Configuration
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

### Step 3: Run Database Services (Docker)
Start PostgreSQL, Redis, and Qdrant in the background:

```bash
docker compose up -d
```

Verify the active containers:
```bash
docker compose ps
```
* **PostgreSQL** runs on port `15432`
* **Redis** runs on port `6379`
* **Qdrant** runs on port `16333` (Dashboard accessible at [http://localhost:16333/dashboard](http://localhost:16333/dashboard))

---

### Step 4: Install Python Dependencies & Run Migrations

#### Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
```

#### Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

Create a superuser account for the dashboard:
```bash
python manage.py createsuperuser
```
*(Enter `admin@adgs.com` and your password).*

---

### Step 5: Start Runtime Services
Open three separate terminal windows to start all components:

#### Terminal 1: Django API Gateway
```bash
# Activate virtualenv
python -m uvicorn django_project.asgi:application --reload --port 8080
```

#### Terminal 2: Celery Background Workers
```bash
# Activate virtualenv
celery -A django_project worker --loglevel=info --pool=solo
```

#### Terminal 3: React Frontend UI
```bash
cd frontend
npm install
npm run dev
```
The application will be accessible at [http://localhost:5173/](http://localhost:5173/) or [http://localhost:5174/](http://localhost:5174/).

---

## 14. Contributing to the Project

I welcome contributions to enhance the safety and governance of enterprise AI. To contribute:
1. **Fork** the repository.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add some amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a **Pull Request** targeting the `v2-django` branch.

Please ensure your code passes all linting and test coverages before opening a PR:
```bash
pytest tests/ -v
```

---

## 15. Future Roadmap & Next Steps

- [ ] **Multi-Tenant Index Isolation:** Support namespaces within Qdrant to segregate documents by department (e.g., HR vectors vs. Finance vectors) with role-based access.
- [ ] **OCR Engine Integration:** Add an automatic `Tesseract` OCR fallback node to parse scanned images/PDFs that don't have text layers.
- [ ] **Custom PII Rules:** Expose an admin panel interface allowing compliance teams to define custom PII regex patterns (e.g., specific employee ID structures).
- [ ] **Direct Slack/Email Alerts:** Send instant notifications to compliance leads when a document is paused for high-risk flags.

---

## 16. Author & Contact
**Md Shahrul Zakaria**  
Software Engineering & Data Science  
* GitHub: [@bringerofdarkness](https://github.com/bringerofdarkness)  
* Email: shahrulzakaria@gmail.com