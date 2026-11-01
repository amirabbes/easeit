# EASEIT

EASEIT is a local AI-assisted HR operations MVP. It combines a React/Vite
frontend, a FastAPI backend, a SQL database, local Ollama models, and an
optional n8n workflow for request classification and routing.

The backend remains the application entry point: the browser calls the backend,
and only the backend communicates with the authenticated n8n webhook. The
n8n token must never be exposed to the browser.

## Architecture

```text
React + Vite frontend
        |
        v
FastAPI backend ---- SQLite (local) / PostgreSQL (Docker Compose)
        |
        +---- Ollama (local models)
        |
        +---- n8n webhook (optional, server-to-server)
```

Included application flows:

- Authenticated dashboards, inbox, message classification, and candidate views
- ATS candidate evaluation and explainable matching in the existing application
- Employee support with authorized policy sources and escalation to HR tickets
- Approval center, employee ticket queue, and audit-chain verification
- Optional n8n intake for HR requests and text-based PDF CVs

## Requirements

- Python 3.11 or newer
- Node.js and npm
- Ollama for local model use
- n8n only if you want to enable workflow orchestration
- Docker Desktop only if you want to run the containerized stack

The local Ollama models used by this project are:

- `llama3.2:3b` for text generation
- `nomic-embed-text` for embeddings (not currently wired into the support
  retrieval flow)

Install the models if needed:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

Check Ollama at `http://localhost:11434`. When the backend runs directly on
Windows, set `OLLAMA_URL=http://localhost:11434`. From a Docker container,
Ollama running on the Windows host is reached at
`http://host.docker.internal:11434`.

## Run locally on Windows

Open separate PowerShell terminals from the repository root.

### 1. Configure the backend

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set a unique `JWT_SECRET`. For a backend running directly on
Windows, set:

```dotenv
OLLAMA_URL=http://localhost:11434
N8N_WEBHOOK_URL=
N8N_WEBHOOK_TOKEN=
```

Leave the n8n settings empty until n8n has been configured. The application
uses SQLite by default for local development.

### 2. Install and start the backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API health endpoint is `http://localhost:8000/api/health`; interactive API
documentation is available at `http://localhost:8000/docs`.

### 3. Install and start the frontend

In another PowerShell terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to the local backend.

## Demo accounts

These seeded credentials are for local development only. Change or remove them
before deploying the application.

| Role | Email | Password |
|---|---|---|
| Recruiter | `recruiter@easeit.local` | `recruiter123` |
| HR manager | `hrmanager@easeit.local` | `hrmanager123` |
| Employee | `employee@easeit.local` | `employee123` |
| Admin | `admin@easeit.local` | `admin123` |

## n8n and Ollama integration

The n8n export is [n8n/new.json](./n8n/new.json). It is deliberately inactive
until its credentials and local services have been configured.

1. Start Ollama and confirm that `llama3.2:3b` is available.
2. Open your n8n instance and import `n8n/new.json`.
3. Configure the Ollama credentials used by the workflow's Ollama model nodes.
   For n8n running directly on Windows, use `http://localhost:11434`. For n8n
   running in Docker while Ollama runs on Windows, use
   `http://host.docker.internal:11434`.
4. Create an n8n **HTTP Header Auth** credential with header name
   `X-EASEIT-N8N-TOKEN` and a private, unique value. Assign it to both
   authenticated webhooks in the workflow.
5. In the repository-root `.env`, configure the same private token and the
   webhook URL for the backend's environment:

   ```dotenv
   N8N_WEBHOOK_URL=http://localhost:5678/webhook/easeit/input
   N8N_WEBHOOK_TOKEN=use-the-same-private-value-as-the-n8n-credential
   ```

   If the backend runs in Docker and n8n runs on the Windows host, use
   `http://host.docker.internal:5678/webhook/easeit/input` for the URL.
6. Activate the workflow in n8n. Do not commit `.env` or share its secrets.

The backend provides:

- `POST /api/workflows/intake` — authenticated HR request intake as JSON.
- `POST /api/workflows/intake/cv` — authenticated HR intake with a PDF upload.

Both routes validate and persist the n8n classification in the existing
database, making the request visible to the application. The backend supports
the `Idempotency-Key` header so a retry of the same request does not create a
duplicate. The browser never receives the n8n token.

Example JSON request (obtain a bearer token from `/api/auth/login`):

```http
POST /api/workflows/intake
Authorization: Bearer <JWT>
Idempotency-Key: 76d106f3-38bb-4d86-b1d4-12c15fcc193c
Content-Type: application/json

{
  "subject": "Interview rescheduling",
  "body": "I want to reschedule my interview scheduled for tomorrow."
}
```

The accepted response includes `request_id`, `execution_id`, `message_id`,
`status`, `classification`, and `duplicate`. The current webhook acknowledges
the request before all downstream workflow branches complete. ATS reports and
n8n approval decisions are not yet synchronized back into the backend.

The support integration sends only employee-visible policy documents and
checks returned source IDs. Without n8n configuration, the existing local
support behavior remains available. Retrieval currently uses lexical matching;
`nomic-embed-text` and ChromaDB are not connected to this flow. PDF uploads
support text-based PDFs up to 5 MB and 30 pages. Scanned PDFs require OCR, which
is not included.

### Workflow safety and scope

- The workflow routes requests for human review where applicable; the LLM does
  not authorize sensitive operations.
- Calendar availability is not claimed unless a real calendar integration
  supplies it.
- IT and training requests are classified for human review; automatic
  assignment to a department ticket queue is not yet connected.
- Email delivery, calendar changes, ATS report synchronization, and approval
  synchronization should not be considered end-to-end features until their
  respective external integrations/callbacks are implemented and tested.

## Run with Docker Compose

Copy `.env.example` to `.env`, then replace `JWT_SECRET` and
`POSTGRES_PASSWORD` with unique values. Use a URL-safe PostgreSQL password
because Compose also inserts it into `DATABASE_URL`.

```powershell
docker compose up --build
```

The Compose stack starts PostgreSQL, MailHog, the backend, and the frontend.
n8n is not included in this Compose file; run/configure it separately. The
backend container is configured to reach Ollama on the Windows host through
`host.docker.internal`. `.env` is ignored by Git and must not be committed.

Useful local addresses:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- MailHog: `http://localhost:8025`
- n8n (when installed separately): `http://localhost:5678`
- Ollama: `http://localhost:11434`

## Validation status

The following local checks have been run:

- Frontend TypeScript check and production build: passed.
- Backend Python compilation and FastAPI import: passed; both workflow intake
  routes are registered.
- n8n export JSON parsing and JavaScript syntax checks for all Code nodes:
  passed.
- Representative workflow routing checks for urgent interview rescheduling,
  candidate CV intake, IT access, training, and employee-policy requests:
  passed against the exported node code.
- Local Ollama generation returned JSON, and `nomic-embed-text` returned a
  768-dimension embedding.
- n8n local health endpoint responded successfully.

The workflow has **not** been imported, credential-bound, and activated in the
local n8n UI yet. Therefore a live backend-to-n8n execution and full
browser-to-workflow test have not been verified. Docker Compose configuration
was checked as YAML, but containers were not started in the validation
environment.

## Known limitations

- This is a local-development MVP, not a production-ready HR system.
- Demo users and seeded synthetic data are for development only.
- Local Ollama generation is optional for existing backend flows; deterministic
  application logic remains available when the model cannot be reached.
- n8n is optional and requires manual import, credential setup, and activation.
- Employee support retrieval is lexical rather than embedding/ChromaDB-based.
- Scanned CV PDFs are not OCR-processed.
- Downstream n8n ATS reports and approval decisions are not yet synchronized
  to the backend.
- Do not use this MVP to make automated candidate rejection or other sensitive
  employment decisions.
