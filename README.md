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

The **Autonomous Data Governance System (ADGS)** is an enterprise-focused AI governance platform designed to intercept, audit, scrub, validate, and govern multi-format files *before* they are allowed to enter a trusted vector database environment.

Most Retrieval-Augmented Generation (RAG) systems directly embed raw organizational data into vector stores. That shortcut may work for demos, but in real enterprise environments it becomes a serious compliance and security problem.

ADGS was built around a different philosophy:

> A vector database should behave like governed production infrastructure — not an uncontrolled document dumping ground.

Every uploaded asset must pass through a stateful governance pipeline involving:

- multi-format parsing
- metadata tracking
- PII detection and scrubbing
- semantic contradiction analysis
- LangGraph checkpoint workflows
- Human-in-the-Loop approval systems
- audit-safe indexing boundaries

The platform combines asynchronous distributed architecture with governance-aware AI workflows to create a production-style compliance layer for enterprise knowledge systems.

---

# Table of Contents

- [Core Problem](#core-problem)
- [Project Objective](#project-objective)
- [System Architecture](#system-architecture)
- [Asynchronous Workflow Lifecycle](#asynchronous-workflow-lifecycle)
- [Technology Stack](#technology-stack)
- [Multi-Format Document Processing](#multi-format-document-processing)
- [Core Features](#core-features)
- [Document Lifecycle](#document-lifecycle)
- [API Blueprint](#api-blueprint)
- [Local Development Setup](#local-development-setup)
- [Roadmap](#roadmap)
- [Security & Governance Principles](#security--governance-principles)
- [Why This Project Matters](#why-this-project-matters)
- [Author](#author)

---

# Core Problem

Traditional RAG systems usually follow this pattern:

```text
Upload Document
    ↓
Chunk Data
    ↓
Generate Embeddings
    ↓
Push Into Vector Database
```

That workflow is simple.

It is also dangerous.

Without governance enforcement, organizations risk pushing:

- Personally Identifiable Information (PII)
- internal legal policies
- payroll data
- employee identifiers
- confidential contracts
- outdated compliance documents
- contradictory corporate definitions

directly into production AI retrieval systems.

Once contaminated knowledge enters a vector database, downstream AI applications inherit those risks automatically.

ADGS exists to stop that from happening.

---

# Project Objective

ADGS introduces a governance-first ingestion architecture for enterprise AI systems.

No uploaded file is trusted automatically.

Every document must pass through a controlled, auditable, asynchronous review pipeline before indexing occurs.

The system performs:

- metadata registration
- document extraction
- structural parsing
- PII mitigation
- semantic conflict evaluation
- governance scoring
- checkpoint-based interruption
- human review approval
- audit tracking
- controlled vector indexing

The goal is to create AI-ready knowledge bases that remain:

- compliant
- explainable
- auditable
- isolated
- production-safe

---

# System Architecture

The platform operates using a distributed asynchronous architecture designed for long-running AI workflows.

```text
       [ React UI Ingestion Client ] (Port 5173)
                    │             ▲
    Multipart Binary│             │ Polling State Logs &
    Asset Streaming ▼             │ Audit Registry Timelines

         [ FastAPI Gateway Layer ] (Port 8080)
                    │
                    ▼
         [ Redis Shared Broker Queue ]
                    │
                    ▼
         [ Celery Asynchronous Workers ]
                    │
                    ▼
         [ LangGraph Stateful Workflow ]
                    │
                    ├──► Multi-Format Extraction Engine
                    ├──► Corporate Asset Classification
                    ├──► PII Scrubbing Engine
                    ├──► Semantic Conflict Detection
                    ├──► Governance Critic Node
                    │
                    ▼
      [ PostgreSQL Checkpoint Persistence ]
                    │
                    ▼
         [ Human Review Interception ]
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
     APPROVED              REJECTED
         │
         ▼
 [ Qdrant Trusted Collection ]
```

---

# Asynchronous Workflow Lifecycle

Large-scale governance analysis is computationally expensive.

Embedding generation, semantic comparison, multi-format extraction, and PII evaluation should never block frontend requests synchronously.

ADGS solves this using an event-driven asynchronous workflow model.

---

## 1. File Upload Phase

The frontend streams a multipart payload to:

```http
POST /documents/upload
```

The FastAPI layer:

- registers metadata in PostgreSQL
- assigns a unique `document_id`
- pushes a task envelope into Redis
- returns an immediate response to the client

This keeps the interface responsive even during heavy workloads.

---

## 2. Background Worker Execution

A Celery worker claims the queued task and spins up an isolated LangGraph execution context.

The orchestration engine begins:

- parsing files
- extracting structured content
- detecting PII
- checking semantic conflicts
- evaluating governance risk

while continuously updating relational state records.

---

## 3. Stateful Workflow Interruption

If the governance engine detects:

- excessive PII exposure
- contradictory clauses
- suspicious semantic overlaps
- policy conflicts
- high-risk compliance patterns

the workflow intentionally pauses itself.

The active graph memory is serialized into PostgreSQL checkpoint tables and the document state changes to:

```text
PAUSED
```

This creates a recoverable governance checkpoint rather than blindly continuing execution.

---

## 4. Human-in-the-Loop Review

The React administration dashboard monitors workflow states continuously.

When a checkpoint interruption appears, administrators can inspect:

- timeline logs
- semantic conflict traces
- risk explanations
- scrubbed content previews
- governance findings

before deciding whether to:

- approve the pipeline
- reject the document
- resume execution
- terminate the workflow

---

## 5. Trusted Vector Indexing

Only approved documents are allowed into the trusted vector environment.

Approved assets are:

- normalized
- chunked
- embedded
- indexed into Qdrant

for downstream retrieval systems.

---

# Technology Stack

| Domain | Technology |
|---|---|
| Backend API | FastAPI |
| Workflow Orchestration | LangGraph |
| Queue System | Celery |
| Broker Layer | Redis |
| Database | PostgreSQL |
| ORM | SQLAlchemy Async |
| Migrations | Alembic |
| Vector Database | Qdrant |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Frontend | React + TypeScript + Vite |
| Authentication | JWT + RBAC |
| Containerization | Docker Compose |

---

# Multi-Format Document Processing

One of the core goals of ADGS was building a deterministic ingestion layer capable of handling different enterprise file structures safely.

The extraction subsystem processes files dynamically based on extension type.

---

## Supported Formats

| Format | Processing Strategy |
|---|---|
| `.txt` | Raw text ingestion |
| `.pdf` | Text-layer extraction using `pypdf` |
| `.docx` | Structured parsing using `python-docx` |
| `.csv` | Relational row serialization |
| `.xlsx` | Spreadsheet flattening using `openpyxl` |
| `.json` | Recursive tree flattening |

---

## Structured Table Handling

CSV and Excel records are serialized into relational string structures like:

```text
Row 12:
Department: Finance
Manager: John Doe
Budget: 2,000,000
```

This preserves relational meaning before vector indexing.

---

## JSON Tree Flattening

Nested JSON configurations are recursively flattened into readable semantic paths:

```text
employee.department.name = Engineering
employee.permissions.admin = true
```

This significantly improves embedding clarity for structured datasets.

---

## OCR-Aware Failure Detection

If extraction layers return empty text payloads, the system flags the document for downstream OCR consideration instead of silently indexing empty vectors.

---

# Core Features

## Stateful LangGraph Checkpoints

Workflow execution can pause and resume without losing orchestration state.

---

## Automated PII Scrubbing

The system detects and sanitizes:

- emails
- phone numbers
- national IDs
- employee identifiers
- explicit identity references

before indexing occurs.

---

## Semantic Conflict Detection

Incoming documents are semantically compared against existing trusted corpora to identify contradictory governance definitions.

---

## Dual-Layer Vector Storage

The platform stores:

- full-document vectors
- chunk-level vectors

to improve retrieval precision.

---

## Audit-Safe Logging

Relational audit trails track workflow transitions without exposing sensitive raw text inside logging structures.

---

## React Administrative Dashboard

The dashboard includes:

- real-time governance metrics
- ingestion monitoring
- conflict inspection
- audit timelines
- vector previews
- approval workflows

---

# Document Lifecycle

```text
[ UPLOADED ]
       │
       ▼
[ PROCESSING ]
       │
       ├──► Conflict / Risk Triggered
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

Generates JWT authorization tokens.

---

## Document Operations

### Upload Documents

```http
POST /documents/upload
```

Secure multipart ingestion endpoint.

---

### Retrieve Documents

```http
GET /documents
```

Returns filtered document registries.

---

### Dashboard Metrics

```http
GET /documents/summary
```

Aggregated governance dashboard metrics.

---

### Workflow Status

```http
GET /documents/{document_id}/status
```

Returns live processing state information.

---

### Audit Logs

```http
GET /documents/{document_id}/audit-logs
```

Chronological governance timeline retrieval.

---

### Resume Workflow

```http
POST /documents/{document_id}/resume
```

Resumes paused LangGraph execution.

---

### Administrative Approval

```http
POST /documents/{document_id}/approve
```

Immediate governance approval override.

---

### Administrative Rejection

```http
POST /documents/{document_id}/reject
```

Terminates the active workflow.

---

### Conflict Validation

```http
POST /documents/{document_id}/conflict-check
```

Triggers semantic contradiction analysis.

---

### Qdrant Vector Preview

```http
GET /documents/{document_id}/qdrant-chunks
```

Returns stored chunk metadata.

---

# Local Development Setup

## 1. Clone Repository

```bash
git clone https://github.com/bringerofdarkness/Autonomous-Data-Governance-System.git

cd Autonomous-Data-Governance-System
```

---

## 2. Configure Environment Variables

Create a `.env` file in the project root using `.env.example`.

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

Verify services:

```bash
docker compose ps
```

Expected active containers:

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

### Run Migrations

```bash
alembic upgrade head
```

### Initialize LangGraph Checkpoints

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
Phase 1  -> Backend Architecture Foundation                  ✅ Completed
Phase 2  -> Redis Queue + Upload Pipelines                   ✅ Completed
Phase 3  -> Automated PII Scrubbing Engine                   ✅ Completed
Phase 4  -> Qdrant Conflict Detection                        ✅ Completed
Phase 5  -> LangGraph PostgreSQL Checkpointing               ✅ Completed
Phase 6  -> Chunk-Level Vector Ingestion                     ✅ Completed
Phase 7  -> Multi-Format Parser Integration                  ✅ Completed
Phase 8  -> Integrated React Governance Dashboard            ✅ Completed
Phase 9  -> Retrieval Synthesis & Generation Layers          🔄 Planned
```

---

# Security & Governance Principles

## Raw Asset Isolation

Raw uploaded files remain isolated from trusted retrieval collections.

---

## PII Boundary Enforcement

Sensitive strings are never indexed directly into production vector stores.

---

## Deterministic Recovery

LangGraph execution states persist using database-backed thread identifiers, allowing safe recovery across crashes and reboots.

---

## Trusted Retrieval Boundaries

Search endpoints only operate against approved vector collections.

Unapproved assets remain fully isolated from downstream AI systems.

---

# Why This Project Matters

Most AI portfolio projects stop at:

```text
Upload PDF → Embed → Chatbot
```

ADGS focuses on the harder production problem:

> How do you safely govern enterprise AI knowledge systems at scale?

This project demonstrates engineering across:

- distributed asynchronous systems
- governance-aware AI infrastructure
- LangGraph orchestration
- vector database architecture
- backend engineering
- checkpoint recovery systems
- enterprise audit workflows
- semantic validation pipelines
- production-style ingestion layers

Instead of being designed like a demo chatbot, ADGS was engineered like an internal enterprise platform.

---

# Author

## Md Shahrul Zakaria

Software Engineering & Data Science

- GitHub: [@bringerofdarkness](https://github.com/bringerofdarkness)

---

# Final Notes

ADGS is not just another RAG ingestion project.

It is a governance infrastructure layer designed to sit *before* enterprise AI systems — protecting retrieval pipelines from unsafe, contradictory, or non-compliant knowledge before it reaches production vector environments.

That separation is the entire philosophy behind the project.

---