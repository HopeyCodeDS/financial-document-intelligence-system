# Financial Document Intelligence System (FDIS)

An AI system for processing sensitive financial documents in regulated environments. FDIS extracts structured data from PDFs using LLMs, enforces compliance through PII masking and audit trails, and provides human-in-the-loop review for high-risk documents.

## Architecture

```
Client (HTTP)
    │
    ▼
┌──────────────────────────────────────────────────────┐
│              FastAPI API Layer (JWT Auth)             │
│  /documents  /extractions  /review  /audit  /health  │
└──────────────────────┬───────────────────────────────┘
                       │ Celery task dispatch
                       ▼
┌──────────────────────────────────────────────────────┐
│               Celery Worker — Pipeline               │
│                                                      │
│  OCR ─→ PII Mask ─→ LLM Extract ─→ Validate ─→ Risk│
│                                                      │
│  Audit logging at every step                         │
└──────┬──────────────┬────────────────┬───────────────┘
       ▼              ▼                ▼
   PostgreSQL       Redis         File Storage
   (primary DB)     (broker)      (documents)
```

## Key Features

- **Multi-engine OCR** — pdfplumber (text-native), docTR (complex layouts), Tesseract (scanned), with automatic engine selection
- **PII masking** — Microsoft Presidio with custom financial recognizers (IBAN, account numbers), AES-256-GCM encrypted reverse mapping
- **LLM extraction** — Structured JSON via Anthropic tool_use API or local models (Ollama/Qwen), with per-field confidence scores
- **Validation engine** — Pluggable rules for financial consistency, completeness, and temporal checks
- **Risk detection** — Flags large transfers, round numbers, high velocity, jurisdiction keywords; auto-triggers human review for MEDIUM+ risk
- **Full audit trail** — Append-only, immutable audit log with DB-enforced write protection
- **Human-in-the-loop review** — Review queue with approve/reject/correct workflow
- **Async processing** — Celery workers for non-blocking document pipeline execution

## Tech Stack


| Layer          | Technology                                     |
| -------------- | ---------------------------------------------- |
| API            | FastAPI, Pydantic v2, Uvicorn                  |
| Database       | PostgreSQL 15, SQLAlchemy 2.0 (async), Alembic |
| Task Queue     | Celery 5.4, Redis 7                            |
| OCR            | pdfplumber, python-doctr, Tesseract            |
| PII            | Microsoft Presidio, spaCy                      |
| LLM            | Anthropic Claude (tool_use), Ollama (local)    |
| Encryption     | AES-256-GCM (cryptography), JWT (python-jose)  |
| Observability  | structlog, Prometheus, OpenTelemetry           |
| Infrastructure | Docker, docker-compose                         |


## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Tesseract OCR (`apt install tesseract-ocr` or equivalent)
- An Anthropic API key (or Ollama for local LLM)

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/your-org/fdis.git
cd fdis/financial-document-intelligence-system
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, APP_SECRET_KEY, JWT_SECRET_KEY,
# PII_ENCRYPTION_KEY, and ANTHROPIC_API_KEY
```

### 2. Generate encryption key

```bash
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
# Paste the output into PII_ENCRYPTION_KEY in .env
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This starts PostgreSQL, Redis, the API server, and a Celery worker.

- **API**: [http://localhost:8000](http://localhost:8000)
- **API docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health check**: [http://localhost:8000/health/live](http://localhost:8000/health/live)

To include Celery Flower monitoring:

```bash
docker-compose --profile monitoring up -d
# Flower UI: http://localhost:5555
```

### 4. Run migrations

```bash
docker-compose exec api alembic upgrade head
```

## Local Development (without Docker)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements/dev.txt

# Download spaCy model (required for PII detection)
python -m spacy download en_core_web_lg

# Start dependencies (PostgreSQL + Redis must be running)
# Then run migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start a Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info
```

## API Usage

### Upload a document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@statement.pdf" \
  -F "document_type=bank_statement"
```

Returns `202 Accepted` with a document ID. Processing runs asynchronously.

### Check extraction status

```bash
curl http://localhost:8000/api/v1/extractions/{document_id} \
  -H "Authorization: Bearer <token>"
```

### Review a flagged document

```bash
curl http://localhost:8000/api/v1/review/pending \
  -H "Authorization: Bearer <token>"
```

## Supported Document Types


| Type             | Description                               |
| ---------------- | ----------------------------------------- |
| `bank_statement` | Bank account statements with transactions |
| `invoice`        | Invoices with line items and totals       |
| `portfolio`      | Investment portfolio summaries            |


## Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires running services)
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=app --cov-report=term-missing
```

## Project Structure

```
app/
├── api/v1/            # FastAPI route handlers
├── config.py          # Pydantic settings
├── core/              # Exceptions, logging, security utilities
├── db/                # Session management, repository pattern
├── models/            # SQLAlchemy ORM models
├── schemas/           # Pydantic request/response schemas
├── pipeline/          # Step-based orchestrator
│   └── steps/         # OCR, PII mask, LLM extract, validate, risk
├── services/          # Business logic
│   ├── audit/         # Append-only audit logger
│   ├── llm/           # LLM client, extractor, prompts
│   ├── ocr/           # Multi-engine OCR with strategy routing
│   ├── pii/           # PII detection, masking, encryption
│   ├── risk/          # Risk detection rules
│   └── validation/    # Validation engine and rule registry
└── tasks/             # Celery task definitions
```

## Security Design

- **PII is never sent to external LLMs** — masked before inference, reversible only at human review
- **AES-256-GCM encryption** for PII mappings and raw LLM responses at rest
- **Immutable audit log** — PostgreSQL trigger prevents UPDATE/DELETE on audit records
- **JWT authentication** on all endpoints except health probes
- **UUID-only filenames** — original filenames never stored on disk

## License

This project is proprietary. All rights reserved.