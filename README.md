# Autonomous Data Governance System (ADGS)

## Project Objective

Autonomous Data Governance System (ADGS) is an AI-powered data governance backend designed to control how enterprise documents enter a trusted knowledge base.

The main objective of this project is to build a governance-first AI pipeline where documents are not directly indexed into a vector database. Instead, every document must pass through a controlled process that includes metadata tracking, PII detection, redaction, conflict detection, human-in-the-loop review, audit logging, and final approval before it becomes part of an approved Gold Collection.

This project is designed for organisations that need safer AI document processing, explainable approval workflows, and controlled retrieval-augmented generation over governed data.

The long-term vision is to support both unstructured and structured data, including text files, PDFs, Word documents, CSV files, Excel files, and database exports.

---

## Current Project Status

This project currently implements a working backend MVP.

The system can upload documents, process them asynchronously, detect and redact PII, check for conflicts against approved documents, pause the workflow for Admin review, resume the workflow through an API call, and safely index approved cleaned content into Qdrant.

Current implementation is focused on `.txt` files to validate the full governance pipeline. Multi-format extraction for PDF, DOCX, CSV, and XLSX is planned next.

---

## Key Features Implemented

- FastAPI backend API
- JWT-based authentication
- Role-based access control
- PostgreSQL database integration
- Alembic database migrations
- Celery background processing
- Redis task broker
- LangGraph workflow orchestration
- PostgreSQL checkpointing for LangGraph state persistence
- Human-in-the-loop pause and resume workflow
- PII detection and redaction
- Cleaned text storage
- Conflict detection using Qdrant vector search
- Admin approval and rejection flow
- Audit logging for governance traceability
- Qdrant Gold Collection indexing
- Local Hugging Face embedding model
- Document-level and chunk-level vector indexing
- Retrieval-only RAG search foundation

---

## Tech Stack

| Area | Technology |
|---|---|
| Backend API | FastAPI |
| Authentication | JWT |
| Authorization | Role-Based Access Control |
| Database | PostgreSQL |
| ORM | SQLAlchemy Async |
| Migrations | Alembic |
| Background Jobs | Celery |
| Message Broker | Redis |
| Workflow Engine | LangGraph |
| Workflow Persistence | LangGraph PostgreSQL Checkpointing |
| Vector Database | Qdrant |
| Embeddings | Hugging Face Sentence Transformers |
| Local Embedding Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Validation | Pydantic |
| Container Services | Docker Compose |
| Language | Python |

---

## Why This Project Matters

Many RAG systems directly ingest and index documents into vector databases. That approach can be risky when documents contain sensitive information, personal data, conflicting business rules, or unapproved internal content.

ADGS follows a safer architecture:

1. Raw documents are stored separately.
2. PII is detected and redacted.
3. Cleaned text is saved separately.
4. Conflicts are checked against approved Gold Collection documents.
5. High-risk or conflicting documents are paused for Admin review.
6. Admin decisions are recorded through audit logs.
7. Only approved cleaned content is indexed into Qdrant.
8. RAG search runs only over approved governed content.

This makes the system suitable for AI governance, compliance-focused document processing, and secure enterprise knowledge base preparation.

---

## High-Level System Architecture

```text
User Upload
    ↓
FastAPI API
    ↓
PostgreSQL Metadata Record
    ↓
Celery Background Task
    ↓
LangGraph Workflow
    ↓
PII Detection and Redaction
    ↓
Cleaned Text Storage
    ↓
Conflict Detection with Qdrant
    ↓
Human-in-the-Loop Pause if Needed
    ↓
Admin Resume / Approve / Reject
    ↓
Approved Cleaned Document
    ↓
Document-Level and Chunk-Level Qdrant Indexing
    ↓
Retrieval-Only RAG Search
```

---

## Governance Workflow

### 1. Document Upload

A user uploads a document through the FastAPI API. The original file is saved in local storage, and metadata is stored in PostgreSQL.

The document starts with the status:

```text
UPLOADED
```

---

### 2. Background Processing

Celery receives a processing task and runs the document through a LangGraph workflow.

The workflow currently includes:

```text
Text Loader
↓
Categorizer
↓
PII Scrubber
↓
Conflict Agent
↓
Critic
↓
HITL Review Node
```

---

### 3. PII Detection and Redaction

The system detects and redacts sensitive information.

Currently supported PII examples:

- Email addresses
- Phone numbers
- Employee IDs
- Labelled person names, such as `Employee Name: John Doe`

The system saves a cleaned version of the document and avoids storing raw PII in audit logs.

---

### 4. Conflict Detection

The cleaned text is embedded locally using a Hugging Face sentence-transformer model.

The vector is compared against existing approved documents in the Qdrant Gold Collection.

If a similar document is found, the system marks:

```text
conflict_found = true
```

and stores a conflict summary.

---

### 5. Human-in-the-Loop Review

If a document is high-risk or has a detected conflict, the LangGraph workflow pauses using an interrupt.

The paused state is persisted in PostgreSQL using LangGraph checkpointing.

The document status becomes:

```text
PAUSED
```

An Admin can resume the workflow later using an API call with a decision:

```text
approve
reject
```

---

### 6. Approval and Indexing

Only approved cleaned documents can be indexed into Qdrant.

If a document has a detected conflict, it must go through the HITL resume workflow before indexing.

This prevents risky or conflicting documents from entering the Gold Collection without Admin review.

---

## Document Status Lifecycle

Documents can move through these statuses:

```text
UPLOADED
PROCESSING
PAUSED
WAITING_FOR_ADMIN
APPROVED
REJECTED
FAILED
```

Current HITL-based flow:

```text
UPLOADED
↓
PROCESSING
↓
PAUSED
↓
APPROVED or REJECTED
↓
Indexed into Qdrant if APPROVED
```

---

## LangGraph PostgreSQL Checkpointing

This project uses LangGraph PostgreSQL checkpointing to persist workflow state.

Each document workflow uses a stable thread ID:

```text
document:<document_id>
```

This allows the workflow to pause and resume later from the same saved state.

This is useful for human-in-the-loop approval, failure recovery, and long-running governance workflows.

---

## Qdrant Gold Collection

Approved documents are indexed into a Qdrant collection:

```text
adgs_gold_documents
```

Current vector configuration:

```text
Vector size: 384
Distance: COSINE
Embedding model: sentence-transformers/all-MiniLM-L6-v2
```

The system supports both:

```text
Document-level vectors
Chunk-level vectors
```

Chunk-level indexing prepares the system for efficient retrieval-augmented generation.

---

## RAG Strategy

The current RAG implementation is retrieval-only.

No external LLM is required at this stage.

The system uses local embeddings and Qdrant search to retrieve approved document chunks.

Future LLM providers such as Gemini, Grok, or other APIs can be added later as optional answer-generation layers.

The intended future RAG flow is:

```text
User question
↓
Local embedding
↓
Qdrant chunk search
↓
Top approved chunks
↓
Optional LLM answer generation
```

This design keeps token usage efficient because only relevant approved chunks will be sent to an LLM.

---

## Current API Features

### Authentication

```text
POST /auth/login
```

### Documents

```text
POST /documents/upload
GET  /documents
GET  /documents/summary
GET  /documents/{document_id}/status
GET  /documents/{document_id}/task-status
GET  /documents/{document_id}/audit-logs
POST /documents/{document_id}/reprocess
POST /documents/{document_id}/resume
POST /documents/{document_id}/approve
POST /documents/{document_id}/reject
POST /documents/{document_id}/index
GET  /documents/{document_id}/qdrant-point
GET  /documents/{document_id}/qdrant-chunks
POST /documents/{document_id}/conflict-check
```

### System

```text
GET  /system/qdrant-health
POST /system/qdrant/gold-collection
```

### RAG

```text
POST /rag/search
```

---

## Current Project Capabilities

The project currently supports:

- Secure document upload
- Metadata tracking in PostgreSQL
- Background document processing with Celery
- Redis-based task queue
- LangGraph-based workflow execution
- PostgreSQL checkpoint persistence
- Human-in-the-loop pause and resume
- PII detection and redaction
- Cleaned text file generation
- Conflict detection against approved documents
- Admin decision tracking
- Audit logs for document lifecycle
- Qdrant document indexing
- Chunk-level vector indexing
- Retrieval-only RAG search over approved chunks

---

## What Has Been Completed

### Backend Foundation

- FastAPI app structure
- Database models
- Authentication
- Role-based authorization
- Docker Compose services
- PostgreSQL connection
- Redis connection
- Qdrant connection
- Alembic migrations

### Document Governance

- Upload endpoint
- Document metadata table
- Document status tracking
- Celery task processing
- Reprocess endpoint
- Status endpoint
- Summary endpoint

### AI Workflow

- LangGraph workflow
- Text loading
- Document categorization
- PII scrubbing
- Conflict detection
- Critic decision logic
- HITL pause node
- HITL resume API

### Governance and Auditability

- Audit log table
- Upload audit logs
- Processing audit logs
- PII detection logs
- Conflict check logs
- HITL pause logs
- HITL approval/rejection logs
- Qdrant indexing logs

### Vector Search and RAG Foundation

- Qdrant Gold Collection
- Local Hugging Face embeddings
- Document-level vector indexing
- Chunk-level vector indexing
- Qdrant point verification
- Chunk verification endpoint
- Retrieval-only RAG search foundation

---

## Planned Improvements

The following features are planned next:

### 1. Multi-Format Extraction Layer

Current processing is focused on `.txt` files.

Planned support:

- PDF
- DOCX
- CSV
- XLSX
- JSON
- Scanned PDF with OCR later

The planned architecture is:

```text
Raw File
↓
Extraction Service
↓
Normalized Text or Structured Profile
↓
Governance Workflow
```

---

### 2. Structured Data Governance

For CSV and Excel files, the system will add:

- Column-level profiling
- Cell-level PII detection
- Sensitive column detection
- Structured risk scoring
- Dataset-level governance summary

---

### 3. Improved PII Detection

Planned improvements:

- Named entity recognition
- More PII types
- Address detection
- National ID pattern support
- Custom organisation-specific PII rules

---

### 4. Advanced Conflict Explanation

Current conflict detection uses similarity search.

Planned improvements:

- Chunk-level conflict explanation
- Side-by-side comparison
- Conflict category detection
- Policy contradiction detection

---

### 5. LLM Answer Generation

Future optional LLM integrations:

- Gemini API
- Grok API
- Local LLM through Ollama
- Other provider-based models

LLMs will be used only after retrieval to reduce token cost.

---

### 6. Dashboard

Planned dashboard options:

- Streamlit dashboard
- React frontend
- Document status cards
- Conflict review panel
- HITL approval UI
- Audit log viewer
- Qdrant indexing status

---

### 7. Testing and Production Hardening

Planned improvements:

- Unit tests
- Integration tests
- Dockerized FastAPI service
- Dockerized Celery worker
- CI/CD pipeline
- Logging improvements
- Error monitoring
- Better configuration management

---

## Local Development Setup

### 1. Clone the repository

```powershell
git clone https://github.com/bringerofdarkness/Autonomous-Data-Governance-System.git
cd Autonomous-Data-Governance-System
```

### 2. Create virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Create environment file

Copy `.env.example` to `.env` and update values if required.

```powershell
copy .env.example .env
```

### 5. Start Docker services

```powershell
docker compose up -d
```

### 6. Run database migrations

```powershell
alembic upgrade head
```

### 7. Set up LangGraph checkpoint tables

```powershell
python -m app.db.setup_langgraph_checkpoints
```

### 8. Start FastAPI

```powershell
python -m uvicorn app.main:app --reload
```

### 9. Start Celery worker

```powershell
celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo
```

### 10. Open Swagger UI

```text
http://127.0.0.1:8000/docs
```

---

## Security and Governance Notes

- Raw uploaded files are stored separately.
- Cleaned text is stored separately.
- Raw PII is not indexed into Qdrant.
- Audit logs do not store actual PII values.
- Conflict documents require HITL approval before indexing.
- LangGraph state is persisted in PostgreSQL.
- Only approved cleaned content enters the Qdrant Gold Collection.
- External LLM calls are not required in the current system.

---

## Project Roadmap

```text
Phase 1: Backend foundation
Status: Completed

Phase 2: Document upload and Celery processing
Status: Completed

Phase 3: PII detection, redaction, and audit logs
Status: Completed

Phase 4: Qdrant Gold Collection and conflict detection
Status: Completed

Phase 5: PostgreSQL checkpointed HITL workflow
Status: Completed

Phase 6: Chunk-level RAG-ready indexing
Status: In Progress

Phase 7: Multi-format extraction
Status: Planned

Phase 8: Retrieval-based RAG answer generation
Status: Planned

Phase 9: Dashboard and UI
Status: Planned

Phase 10: Production testing and deployment
Status: Planned
```

---

## Recruiter Summary

This project demonstrates backend engineering, data engineering, and AI engineering skills through a governance-first AI document pipeline.

It combines FastAPI, PostgreSQL, Celery, Redis, LangGraph, Qdrant, local Hugging Face embeddings, audit logging, and human-in-the-loop workflow design.

The system is designed to safely prepare enterprise documents for future RAG applications while protecting sensitive information and maintaining approval traceability.

---

## Author

Built by [Md Shahrul Zakaria](https://github.com/bringerofdarkness)