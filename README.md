# Autonomous Data Governance System (ADGS)

<div align="center">

[![Backend API](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Workflow Orchestration](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![Vector DB](https://img.shields.io/badge/VectorDB-Qdrant-red.svg?style=flat-square)](https://qdrant.tech/)
[![Task Queue](https://img.shields.io/badge/Queue-Celery%20%26%20Redis-green.svg?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-336791.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Frontend UI](https://img.shields.io/badge/Frontend-React%20%26%20Vite-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://react.dev/)

</div>

---

## Overview

The **Autonomous Data Governance System (ADGS)** is an enterprise-grade AI governance platform built to solve one of the biggest hidden problems in modern RAG pipelines:

> Organizations are pushing raw internal documents directly into vector databases without enforcing governance, compliance validation, or privacy isolation.

ADGS introduces a strict governance-first ingestion architecture where every uploaded document must pass through a controlled, auditable, asynchronous workflow before it can enter the trusted knowledge layer.

Instead of treating vector databases like a dumping ground for enterprise data, ADGS treats them as **regulated production infrastructure**.

The platform combines:

- FastAPI asynchronous APIs
- LangGraph stateful orchestration
- Celery distributed workers
- PostgreSQL checkpoint persistence
- Qdrant semantic validation
- React administrative dashboards
- Automated PII scrubbing pipelines

to create a fully traceable governance system for AI-ready corporate knowledge bases.

---

# Table of Contents

- [Core Problem](#core-problem)
- [Project Objective](#project-objective)
- [System Architecture](#system-architecture)
- [Asynchronous Processing Lifecycle](#asynchronous-processing-lifecycle)
- [Technology Stack](#technology-stack)
- [Core Features](#core-features)
- [Governance Workflow](#governance-workflow)
- [Document State Lifecycle](#document-state-lifecycle)
- [API Blueprint](#api-blueprint)
- [Local Development Setup](#local-development-setup)
- [Roadmap](#roadmap)
- [Security & Governance Principles](#security--governance-principles)
- [Why This Project Matters](#why-this-project-matters)
- [Author](#author)

---

# Core Problem

Traditional Retrieval-Augmented Generation (RAG) systems usually follow a dangerous shortcut:

```text
Upload Document -> Chunk -> Embed -> Store in Vector DB
```

That sounds efficient.

It is also a compliance nightmare.

This architecture can accidentally expose:

- Personally Identifiable Information (PII)
- internal legal clauses
- confidential employee records
- outdated policy definitions
- contradictory governance documents
- regulated customer information

inside production AI systems.

Once contaminated data enters the vector layer, downstream AI applications inherit those risks automatically.

ADGS exists specifically to prevent that scenario.

---

# Project Objective

ADGS enforces a strict governance pipeline before knowledge-base indexing occurs.

No document is trusted automatically.

Every uploaded asset moves through:

- ingestion validation
- metadata tracking
- classification
- PII detection
- semantic contradiction analysis
- human review checkpoints
- approval enforcement
- audit logging
- controlled vector indexing

The final goal is to create:

- compliant AI-ready datasets
- explainable governance workflows
- auditable document histories
- safe vector database environments
- production-grade enterprise AI infrastructure

---

# System Architecture

The platform operates using an event-driven asynchronous architecture.

```text
       [ React Administration Dashboard ] (Port 5173)
                    │             ▲
    Multipart Upload│             │ Live Polling + Audit Timelines
                    ▼             │
         [ FastAPI Gateway Layer ] (Port 8080)
                    │
                    ▼
         [ Redis Broker Queue ]
                    │
                    ▼
       [ Celery Distributed Workers ]
                    │
                    ▼
      [ LangGraph Stateful Workflow ]
                    │
                    ├──► Text Loader & Parsing
                    ├──► Asset Classification
                    ├──► PII Scrubbing Engine
                    ├──► Semantic Conflict Detection
                    ├──► Governance Critic Evaluation
                    │
                    ▼
      [ PostgreSQL Checkpoint Storage ]
                    │
          Workflow Interruption
                    │
                    ▼
         [ Human Approval Layer ]
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
   APPROVED              REJECTED
         │
         ▼
[ Qdrant Production Index ]
```

---

# Asynchronous Processing Lifecycle

Because embedding generation, semantic analysis, and governance validation are computationally expensive, ADGS separates ingestion from processing using asynchronous worker orchestration.

---

## 1. Upload Phase

The frontend streams a multipart document payload to:

```http
POST /documents/upload
```

The backend:

- stores metadata in PostgreSQL
- generates a unique `document_id`
- queues a background task in Redis
- instantly returns a response to the client

This keeps the UI responsive even for large uploads.

---

## 2. Worker Execution Phase

A Celery worker claims the queued task and spins up an isolated LangGraph execution context.

The graph begins processing:

- extraction
- classification
- PII analysis
- contradiction detection
- governance evaluation

while continuously updating relational status records.

---

## 3. Stateful Governance Intercept

If the system detects:

- high-risk PII
- contradictory clauses
- suspicious governance patterns
- compliance anomalies

the LangGraph workflow intentionally pauses execution.

The entire workflow state is checkpointed into PostgreSQL and the document status changes to:

```text
PAUSED
```

This creates a recoverable governance checkpoint.

---

## 4. Human-in-the-Loop Approval

Administrators review:

- audit timelines
- semantic conflicts
- risk explanations
- scrubbed content previews

from the React dashboard.

They can then:

- approve the workflow
- reject the workflow
- resume execution
- terminate the pipeline

without losing orchestration state.

---

## 5. Production Indexing

Only approved assets are allowed into the trusted vector layer.

Approved documents are:

- chunked
- embedded
- normalized
- indexed into Qdrant

for downstream retrieval systems.

---

# Technology Stack

| Domain | Technologies |
|---|---|
| Backend API | FastAPI |
| Workflow Orchestration | LangGraph |
| Task Queue | Celery |
| Broker Layer | Redis |
| Database | PostgreSQL |
| ORM | SQLAlchemy Async |
| Migrations | Alembic |
| Vector Database | Qdrant |
| Embeddings | Sentence Transformers |
| Frontend | React + Vite + TypeScript |
| Containerization | Docker Compose |
| Authentication | JWT + RBAC |

---

# Core Features

## Governance & AI Workflow Features

### Stateful Workflow Interruptions

LangGraph checkpoint persistence allows workflows to pause and resume without losing execution context.

---

### Automated PII Scrubbing

The platform detects and sanitizes:

- emails
- phone numbers
- national IDs
- employee references
- explicit identity markers

before vector indexing occurs.

---

### Semantic Contradiction Detection

Incoming assets are semantically compared against trusted vector corpora to detect conflicting governance definitions before approval.

---

### Dual-Layer Vector Indexing

The system stores:

- full-document vectors
- chunk-level vectors

to improve downstream retrieval precision.

---

### Full Audit Traceability

Every workflow transition is stored relationally for compliance review and forensic inspection.

---

# Governance Workflow

```text
Upload
   │
   ▼
Metadata Registration
   │
   ▼
Asynchronous Queue Dispatch
   │
   ▼
LangGraph Orchestration
   │
   ├──► File Parsing
   ├──► Classification
   ├──► PII Scrubbing
   ├──► Semantic Conflict Analysis
   └──► Governance Evaluation
   │
   ▼
Checkpoint Intercept
   │
   ├──► Approve
   └──► Reject
   │
   ▼
Production Vector Indexing
```

---

# Document State Lifecycle

```text
[ UPLOADED ]
       │
       ▼
[ PROCESSING ]
       │
       ├──► Conflict / Risk Detected
       │                │
       │                ▼
       │           [ PAUSED ]
       │                │
       │        ┌───────┴───────┐
       │        │               │
       │        ▼               ▼
       │   APPROVED         REJECTED
       │
       ▼
[ QDRANT INDEXED ]
```

---

# API Blueprint

## Authentication

```http
POST /auth/login
```

Generates JWT authentication tokens.

---

## Document Operations

```http
POST /documents/upload
```

Secure multipart document upload.

```http
GET /documents
```

Retrieve filtered document registries.

```http
GET /documents/summary
```

Aggregated governance dashboard metrics.

```http
GET /documents/{document_id}/status
```

Returns real-time workflow status.

```http
GET /documents/{document_id}/audit-logs
```

Retrieves chronological audit timelines.

```http
POST /documents/{document_id}/resume
```

Resumes paused LangGraph execution.

```http
POST /documents/{document_id}/approve
```

Administrative approval override.

```http
POST /documents/{document_id}/reject
```

Terminates the governance pipeline.

```http
POST /documents/{document_id}/conflict-check
```

Runs forced semantic contradiction analysis.

```http
GET /documents/{document_id}/qdrant-chunks
```

Returns chunk-level vector metadata.

---

## Vector Search

```http
POST /rag/search
```

Retrieval-only search endpoint over approved knowledge collections.

---

# Local Development Setup

## 1. Clone Repository

```bash
git clone https://github.com/bringerofdarkness/Autonomous-Data-Governance-System.git

cd Autonomous-Data-Governance-System
```

---

## 2. Configure Environment Variables

Create a `.env` file in the root directory using `.env.example`.

Then create another `.env` inside the `frontend/` directory:

```env
VITE_API_BASE_URL=http://127.0.0.1:8080
```

---

## 3. Start Infrastructure Services

Ensure Docker Desktop is running.

```bash
docker compose up -d
```

Verify active containers:

```bash
docker compose ps
```

Expected services:

- PostgreSQL
- Redis
- Qdrant

---

## 4. Install Backend Dependencies

```bash
python -m venv .venv
```

### Windows PowerShell

```bash
.\.venv\Scripts\Activate.ps1
```

### Install Requirements

```bash
pip install -r requirements.txt
```

### Run Database Migrations

```bash
alembic upgrade head
```

### Initialize LangGraph Checkpoint Tables

```bash
python -m app.db.setup_langgraph_checkpoints
```

---

## 5. Launch Runtime Services

### Terminal 1 — FastAPI Server

```bash
.\.venv\Scripts\Activate.ps1

python -m uvicorn app.main:app --reload --port 8080
```

---

### Terminal 2 — Celery Workers

```bash
.\.venv\Scripts\Activate.ps1

celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo
```

---

### Terminal 3 — React Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# Roadmap

```text
Phase 1  -> Backend Architecture Foundation                ✅ Completed
Phase 2  -> Redis Queue + Upload Pipeline                  ✅ Completed
Phase 3  -> Automated PII Scrubbing                        ✅ Completed
Phase 4  -> Qdrant Conflict Validation                     ✅ Completed
Phase 5  -> LangGraph PostgreSQL Checkpointing             ✅ Completed
Phase 6  -> Chunk-Level Vector Architecture                ✅ Completed
Phase 7  -> React Governance Dashboard                     ✅ Completed
Phase 8  -> Multi-Format Extraction (PDF/CSV)              🔄 Planned
Phase 9  -> Retrieval Synthesis & Generation Layer         🔄 Planned
```

---

# Security & Governance Principles

## Separation of Raw Assets

Raw uploaded content is isolated from production retrieval systems.

---

## PII Isolation Enforcement

Unredacted sensitive strings are never indexed into vector collections.

---

## Deterministic Checkpoint Recovery

LangGraph execution states persist using database-backed thread identifiers for reliable recovery.

---

## Trusted Knowledge Boundaries

Only approved assets inside trusted collections are searchable through retrieval endpoints.

---

# Why This Project Matters

Most AI portfolio projects stop at:

```text
Upload PDF -> Embed -> Chatbot
```

ADGS focuses on the harder production problem:

> How do you govern AI knowledge systems safely at enterprise scale?

This project demonstrates practical engineering across:

- asynchronous distributed systems
- AI orchestration pipelines
- governance-first architecture
- vector infrastructure
- backend engineering
- workflow checkpointing
- compliance-aware retrieval systems
- stateful orchestration
- enterprise auditability

Instead of relying on thin wrappers or simplified demos, the platform was engineered like an internal enterprise system.

---

# Author

## Md Shahrul Zakaria

Software Engineering & Data Science

- GitHub: [@bringerofdarkness](https://github.com/bringerofdarkness)

---

# Final Notes

ADGS is not designed as a generic chatbot backend.

It is designed as a governance infrastructure layer that sits *before* enterprise AI systems — protecting retrieval pipelines from unsafe, contradictory, or non-compliant data before it ever reaches production vector environments.

That separation is the entire philosophy behind the project.

---