# Autonomous Data Governance System (ADGS)

<p align="center">
  <b>
    Production-Grade Asynchronous Semantic Firewall, Compliance Gatekeeper,
    and Human-in-the-Loop AI Governance Pipeline for Enterprise RAG Systems
  </b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Django-REST%20Framework-092E20?logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/React-Vite%20%26%20TS-61DAFB?logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/PostgreSQL-Metadata%20Core-4169E1?logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Qdrant-Vector%20Store-DC244C" />
  <img src="https://img.shields.io/badge/Redis-Message%20Broker-DC382D?logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Celery-Task%20Queue-3771A1?logo=celery&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-Workflow%20Orchestrator-1C3C3C" />
  <img src="https://img.shields.io/badge/Google--Gemini-LLM%20Synthesis-blue" />
  <img src="https://img.shields.io/badge/SentenceTransformers-all--MiniLM--L6--v2-yellow" />
  <img src="https://img.shields.io/badge/Docker-Services-2496ED?logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Pytest-Tests-0A9EDC?logo=pytest&logoColor=white" />
</p>

---
---

# 📺 Interface Demonstration & Visual Showcases

> [!NOTE]  
> **Corporate Security & Compliance Panel:** ADGS features an interactive React-based dashboard that monitors incoming file streams, lets administrators inspect flagged PII and contradictions, and enables manual vector indexing overrides.

<p align="center">
  <b>1. Governance Overview Dashboard</b><br/>
  <img src="assets/overview.png" alt="Governance Overview Dashboard" width="90%" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); margin-bottom: 20px;" />
</p>

<p align="center">
  <b>2. Document Governance Registry</b><br/>
  <img src="assets/documents.png" alt="Document Governance Registry" width="90%" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); margin-bottom: 20px;" />
</p>

<p align="center">
  <b>3. RAG Synthesis Engine (Intelligence Hub)</b><br/>
  <img src="assets/rag.png" alt="RAG Synthesis Engine" width="90%" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);" />
</p>

*The visual interface maps to the entire security lifecycle: File Ingestion ➔ Worker Analysis ➔ Admin Review/Pause ➔ Qdrant Vector Commits ➔ Context-Locked Chat.*

---

# Table of Contents

- [Overview](#overview)
- [Why ADGS? (The Scenario)](#why-adgs-the-scenario)
- [Key Features & Benefits](#key-features-&-benefits)
- [Supported Formats & Extraction Strategies](#supported-formats-&-extraction-strategies)
- [Pre-Build Conception & System Design](#pre-build-conception-&-system-design)
- [System Architecture Overview](#system-architecture-overview)
- [Codebase Map & File Responsibilities](#codebase-map-&-file-responsibilities)
- [Most Challenging Parts (The Engineering Hurdles)](#most-challenging-parts-the-engineering-hurdles)
- [Learnings & Takeaways](#learnings-&-takeaways)
- [Local Development Setup](#local-development-setup)
- [Contributing to the Project](#contributing-to-the-project)
- [Future Roadmap & Next Steps](#future-roadmap-&-next-steps)
- [Author & Contact](#author-&-contact)

---

# Overview

The **Autonomous Data Governance System (ADGS)** is an enterprise-focused semantic firewall built to secure Retrieval-Augmented Generation (RAG) databases. Rather than naive ingestion systems that chunk and vectorize raw corporate uploads immediately, ADGS intercepts, audits, sanitizes, and evaluates documents within a distributed task-queue architecture. Powered by a stateful cyclical **LangGraph** workflow and backed by **Celery/Redis**, ADGS halts high-risk files (PII exposure, semantic contradictions) for human review before vectorization occurs.

---

# Why ADGS? (The Scenario)

### Before ADGS: The Customer Service Contamination
Suppose a company uses an internal RAG chatbot for customer support. An employee uploads a spreadsheet with customer names, phone numbers, and SSNs, alongside an old draft stating: *"Refunds are valid up to 45 days"* (the active company policy is 14 days).

* **The Exposure:** The spreadsheet goes directly into the vector store.
* **The Exploit:** A regular user asks: *"What is customer John Doe's phone number?"* The chatbot retrieves the raw phone number from the vector store and outputs it. A support agent asks: *"What is our refund window?"* The chatbot retrieves the old 45-day policy, causing financial leakage.
* **Result:** Compliance violations (GDPR/HIPAA), data leaks, and brand trust erosion.

### After ADGS: The Solution
1. **Upload & Intercept:** The employee uploads the spreadsheet. ADGS intercepts it, saving the raw asset in private storage.
2. **PII Sanitizer:** The system scans the document, redacting all names, phone numbers, and SSNs.
3. **Conflict Agent:** The system generates embeddings of the document segments, queries Qdrant to search for semantic overlaps, and flags that the "45-day refund window" contradicts the existing approved "14-day refund policy."
4. **Critic Node:** Calculating a high risk score, the workflow halts itself and serializes its state into PostgreSQL.
5. **Human-in-the-Loop (HITL):** An admin reviews the flagged contradictions and redacted PII on the dashboard, clicking **REJECT**.
6. **Result:** The vector database remains clean and compliant. The dangerous data never enters the vector index.

---

# Key Features & Benefits

* **PII Leakage Prevention:** Automatically redacts sensitive identifiers (emails, phone numbers, SSNs, IDs) before vectorization.
* **Semantic Integrity Audits:** Scans new documents for contradictions against existing knowledge to prevent hallucination.
* **Human-in-the-Loop (HITL) Gate:** Pauses high-risk workflows for administrator approval using database-backed checkpoints.
* **Asynchronous Web Scalability:** Decouples heavy AI workloads from web workers to maintain high web API responsiveness.
* **Immutability of Audit Trails:** Records state changes and admin decisions in PostgreSQL for security compliance.

---

# Supported Formats & Extraction Strategies

ADGS uses specialized adapters to extract text from different file structures without losing relational meaning:

| Format | Parsing Engine | Ingestion Strategy | Use Case |
| :--- | :--- | :--- | :--- |
| **`.pdf`** | `pypdf` | Page-by-page text extraction, OCR-ready empty layer checks. | Manuals, agreements, policy files. |
| **`.docx`** | `python-docx` | Relational table extraction and paragraph structural mapping. | Legal contracts, proposals. |
| **`.xlsx`** | `openpyxl` | Row-by-row relational serialization and sheet flattening. | Financial worksheets, reports. |
| **`.csv`** | Python built-in | Relational record flattening (e.g., `Row 12 - Name: X, ID: Y`). | Structured user lists, system logs. |
| **`.json`** | Python built-in | Recursive key-path flattening (e.g., `user.auth.role = Admin`). | Configuration files, structured API data. |
| **`.txt`** | Python built-in | Raw text segment reading. | Plain logs, readmes, text notes. |

---

# Pre-Build Conception & System Design

### Pre-Building Ideation (The Design Philosophy)
Before writing the first line of code, the system was designed around three architectural constraints:
1. **AI Ingest is an Untrusted Write Operation:** In classic web development, we never run raw SQL queries from client input without sanitizing them. We must treat document uploads for AI ingestion with the same suspicion. Every file must pass through a strict semantic and structural sanitization pipeline.
2. **Heavy Computations Must Be Decoupled:** Parsing large documents, running local transformer embeddings, searching vectors, and invoking LLMs are computationally heavy operations. Running these synchronously on the web-request thread blocks the server. The architecture had to run asynchronously using background workers.
3. **State Integrity Across Interruptions:** Because human approval is required for high-risk files, the system needed a way to pause mid-workflow, serialize its execution memory, and resume cleanly without losing context or restarting the pipeline.

### Planning the Migration (V1 to V2)
* **V1 Prototype (FastAPI):** Built a lightweight, async API using FastAPI, SQLAlchemy Async, and a basic regex PII scrubber. Focus was on building the extraction and vector lookup mechanics.
* **V2 Production Migration (Django + LangGraph + Celery):** Migrated to Django and DRF to gain stable ORM transactions, secure migrations, and a ready-made administrative interface (Django Admin). Integrated Celery for queue offloading, and rebuilt the pipeline using a cyclical state machine in LangGraph to handle human-in-the-loop checkpoints.

---

# System Architecture Overview

```text
[ User Ingestion & Chat Client ] <--> [ Django REST Framework Gateway ]
                                                    │
                                   ┌────────────────┴────────────────┐
                                   ▼                                 ▼
                     [ PostgreSQL Database ]             [ Redis Task Queue Broker ]
                   - Relational metadata                             │
                   - LangGraph Checkpoints                           ▼
                                                       [ Celery Async Workers ]
                                                                     │
                                                                     ▼
                                                      [ LangGraph Workflows ]
                                                       - text_loader_node
                                                       - categorizer_node
                                                       - pii_scrubber_node
                                                       - conflict_agent_node
                                                       - critic_node
                                                       - hitl_review_node
                                                                     │
                                                       ┌─────────────┴─────────────┐
                                                       ▼ (If Approved)             ▼ (If Flagged)
                                              [ Indexing Service ]            [ PAUSED State ]
                                                       │                               │
                                                       ▼                               ▼
                                             [ Qdrant Vector DB ]            [ Admin Panel Review ]
                                             (Gold Collection)
```

---

# Codebase Map & File Responsibilities

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

# Most Challenging Parts (The Engineering Hurdles)

### 1. LangGraph Checkpointing in a Distributed Celery Context
* **The Challenge:** LangGraph's human-in-the-loop pause requires serializing the execution state into a database. When running inside Celery background tasks, managing database connections across separate worker processes is tricky.
* **The Solution:** I implemented the `PostgresSaver` checkpointer using a raw `psycopg` connection, passing it to the graph compilation stage. When the Critic Node pauses, the state is safely saved in PostgreSQL. Once an admin hits `/resume`, a new Celery task is spawned, loads the thread ID from the DB checkpointer, and picks up exactly where the workflow left off.

### 2. Semantic Contradiction Mapping (Conflict Agent)
* **The Challenge:** Determining if a document contradicts existing information without causing false positives. For example, updating a phone number is an update, not necessarily a dangerous contradiction, but changing a legal policy is.
* **The Solution:** The Conflict Agent generates dense vectors of the new text chunks, queries Qdrant to pull the top 3 semantically closest chunks, and feeds both texts to the Gemini LLM with a specialized system prompt. The model evaluates whether the differences constitute a logical contradiction, flagging them for human review.

### 3. Preserving Layout Meaning in Structural Formats (CSV/JSON/Excel)
* **The Challenge:** Vector databases require text chunks. Pushing raw CSV lines (`John,Doe,34,Admin`) causes the embedding model to lose the connection between values and headers.
* **The Solution:** I built custom parser adapters. CSV/Excel sheets are flattened relationally (e.g., `Row 12 - Name: John Doe, Age: 34, Role: Admin`), while nested JSONs are converted into fully qualified path strings. This keeps the semantic context clean for the vectorizer.

---

# Learnings & Takeaways

* **Decoupling is Crucial for AI Pipelines:** AI workloads are heavy and slow. Wrapping everything in synchronous API calls causes timeouts and server crashes. Background queueing via Celery is essential for any production-grade AI system.
* **Input Sanitization Applies to AI:** We must treat unstructured text inputs with the same validation mindset as structured JSON inputs. Protecting the vector store is the only way to build secure corporate RAG systems.
* **State Machines Ease Complex Workflows:** Managing multistage pipelines (Extract ➔ Categorize ➔ Scrub ➔ Audit ➔ Review ➔ Index) with raw Python code becomes a spaghetti mess. Using a graph-based state machine (LangGraph) makes the execution deterministic, structured, and easy to modify.

---

# Local Development Setup

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

# Contributing to the Project

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

# Future Roadmap & Next Steps

- [ ] **Multi-Tenant Index Isolation:** Support namespaces within Qdrant to segregate documents by department (e.g., HR vectors vs. Finance vectors) with role-based access.
- [ ] **OCR Engine Integration:** Add an automatic `Tesseract` OCR fallback node to parse scanned images/PDFs that don't have text layers.
- [ ] **Custom PII Rules:** Expose an admin panel interface allowing compliance teams to define custom PII regex patterns (e.g., specific employee ID structures).
- [ ] **Direct Slack/Email Alerts:** Send instant notifications to compliance leads when a document is paused for high-risk flags.

---

# Author & Contact
**Md Shahrul Zakaria**  
Software Engineering & Data Science  
* GitHub: [@bringerofdarkness](https://github.com/bringerofdarkness)  
* Email: shahrulzakaria@gmail.com