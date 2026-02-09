# Google Cloud Financial Advisor

An intelligent compliance assistant powered by **Google ADK** (Agent Development Kit) and **Neo4j Agent Memory Context Graphs**, demonstrating multi-agent AI for KYC/AML compliance, fraud detection, and relationship intelligence.

<!-- ![Financial Advisor Dashboard](docs/screenshots/dashboard-overview.png) -->

## Overview

This example application showcases the Google Cloud-Neo4j integration through a production-ready architecture for financial services compliance. It demonstrates how AI agents can leverage graph-based memory for explainable, auditable decision-making.

### Key Features

- **Multi-Agent Investigation**: Coordinated KYC, AML, relationship, and compliance analysis using Google ADK
- **Context Graph Intelligence**: Relationship mapping and network analysis with Neo4j
- **Explainable AI**: Full audit trails for regulatory compliance (EU AI Act ready)
- **Real-time Monitoring**: Transaction and behavior pattern detection
- **Graph-based RAG**: Reduces hallucinations through grounded, relationship-aware retrieval

---

## Sample Prompts

> Run a full compliance investigation on CUST-003 Global Holdings Ltd — check KYC documents, scan for structuring patterns, trace the shell company network, and screen against sanctions lists"

> I see four cash deposits of $9,500 each from CUST-003 in late January. Analyze whether this is a structuring pattern and identify where the funds went"

> Compare the risk profiles of all three customers and flag which ones need enhanced due diligence"

> Trace the beneficial ownership chain from Global Holdings Ltd through Shell Corp Cayman and Anonymous Trust Seychelles — who ultimately controls these entities?"

> Maria Garcia (CUST-002) has rapid wire transfers totaling over $280K. Investigate whether her import/export business justifies this transaction volume"

> Generate a Suspicious Activity Report for the $250,000 wire from an unknown offshore entity to CUST-003 that was moved to Shell Corp Cayman the next day"


Here's what each prompt demonstrates:

1. **Full multi-agent orchestration** — explicitly requests all 4 specialist agents (KYC, AML, Relationship, Compliance) to work together on one investigation
2. **AML pattern detection** — highlights the structuring pattern ($9,500 deposits just under the $10K reporting threshold) and fund tracing
3. **Cross-customer comparison** — engages KYC across all 3 risk profiles (low/medium/high), showing the range of the demo data
4. **Relationship/shell company analysis** — deep network tracing through the BVI → Cayman → Seychelles corporate layers
5. **Transaction velocity analysis** — focuses on CUST-002 (Maria Garcia), who's underutilized in the current prompts, and triggers the AML agent's velocity analysis
6. **SAR generation** — triggers the Compliance agent's `generate_sar_report` tool on a specific suspicious transaction

## Getting Started Tutorial

This tutorial walks you through setting up the Financial Advisor from scratch, including Google Cloud configuration, Neo4j setup, and running your first compliance investigation.

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **uv** - Fast Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **Docker Desktop** - [Download Docker](https://www.docker.com/products/docker-desktop/)
- **Google Cloud CLI** - [Install gcloud](https://cloud.google.com/sdk/docs/install)

---

### Step 1: Set Up Google Cloud Project

First, create and configure a Google Cloud project with the required APIs.

#### 1.1 Create a New Project (or use an existing one)

```bash
# Create a new project
gcloud projects create my-financial-advisor --name="Financial Advisor"

# Set it as the current project
gcloud config set project my-financial-advisor
```

<!-- ![Google Cloud Console - Create Project](docs/screenshots/gcp-create-project.png) -->

#### 1.2 Enable Required APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

#### 1.3 Set Up Authentication

For local development, authenticate with Application Default Credentials:

```bash
gcloud auth application-default login
```

This opens a browser for you to authenticate. Once complete, your credentials are stored locally and will be used by the application.

<!-- ![gcloud auth login browser](docs/screenshots/gcp-auth-browser.png) -->

#### 1.4 Verify Vertex AI Access

Test that you can access Vertex AI:

```bash
gcloud ai models list --region=us-central1 --limit=5
```

You should see a list of available models. If you get a permission error, ensure the Vertex AI API is enabled and you have the required roles.

---

### Step 2: Set Up Neo4j

You have two options: **Neo4j Aura** (cloud, recommended) or **Local Neo4j** (Docker).

#### Option A: Neo4j Aura (Recommended for Production)

1. Go to [Neo4j Aura Console](https://console.neo4j.io/)
2. Click **Create Instance** → Select **Free** tier
3. Choose a cloud provider and region (ideally close to your Google Cloud region)
4. Wait for the instance to be created (~2 minutes)
5. **Save the password** shown - you won't see it again!
6. Copy the **Connection URI** (looks like `neo4j+s://xxxxxxxx.databases.neo4j.io`)

<!-- ![Neo4j Aura Console - Create Instance](docs/screenshots/neo4j-aura-create.png) -->

<!-- ![Neo4j Aura Console - Connection Details](docs/screenshots/neo4j-aura-connection.png) -->

#### Option B: Local Neo4j with Docker

For local development and testing:

```bash
# Start Neo4j with Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5-community
```

Local connection details:
- **URI**: `bolt://localhost:7687`
- **Username**: `neo4j`
- **Password**: `password123`

Access Neo4j Browser at http://localhost:7474 to verify it's running.

<!-- ![Neo4j Browser - Local Instance](docs/screenshots/neo4j-browser-local.png) -->

---

### Step 3: Clone and Configure the Project

#### 3.1 Navigate to the Example

```bash
cd examples/google-cloud-financial-advisor
```

#### 3.2 Create Your Environment File

```bash
cp .env.example .env
```

#### 3.3 Edit `.env` with Your Credentials

Open `.env` in your editor and fill in your values:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=my-financial-advisor          # Your GCP project ID
VERTEX_AI_LOCATION=us-central1                     # Or your preferred region
VERTEX_AI_MODEL_ID=gemini-2.0-flash               # Gemini model for agents
VERTEX_AI_EMBEDDING_MODEL=text-embedding-004       # Embedding model

# Neo4j Configuration
# For Aura:
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-aura-password

# For Local Docker:
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=password123

# Application Settings
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

### Step 4: Install Dependencies

The project uses **uv** for Python (backend) and **npm** for Node.js (frontend).

#### 4.1 Install Everything with Make

```bash
make install
```

This runs:
- `cd backend && uv sync` - Installs Python dependencies
- `cd frontend && npm install` - Installs Node.js dependencies

#### 4.2 Manual Installation (Alternative)

If you prefer to run commands manually:

```bash
# Backend
cd backend
uv sync
cd ..

# Frontend
cd frontend
npm install
cd ..
```

<!-- ![Terminal - make install output](docs/screenshots/terminal-make-install.png) -->

---

### Step 5: Load Sample Data

Load example customers, organizations, and transactions into Neo4j:

```bash
make load-data
```

Or manually:

```bash
cd backend
uv run python -m src.data.load_sample_data
```

You should see output like:

```
INFO:__main__:Connecting to Neo4j at neo4j+s://...
INFO:__main__:Clearing existing data...
INFO:__main__:Creating constraints...
INFO:__main__:Loading customers...
INFO:__main__:  Created customer: Alice Johnson
INFO:__main__:  Created customer: Bob Smith
...
INFO:__main__:Done!
```

<!-- ![Terminal - Sample data loaded](docs/screenshots/terminal-load-data.png) -->

#### Verify Data in Neo4j Browser

Open Neo4j Browser and run:

```cypher
MATCH (n) RETURN labels(n)[0] AS type, count(*) AS count
```

You should see counts for Customer, Organization, and Transaction nodes.

<!-- ![Neo4j Browser - Data verification](docs/screenshots/neo4j-verify-data.png) -->

---

### Step 6: Start the Application

#### 6.1 Start All Services

```bash
make dev
```

This starts:
- **Neo4j** (Docker) - if using local Neo4j
- **Backend** (FastAPI) - http://localhost:8000
- **Frontend** (Vite) - http://localhost:5173

#### 6.2 Or Start Services Separately

In separate terminal windows:

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

#### 6.3 Verify Services Are Running

- **Frontend**: Open http://localhost:5173 - You should see the Financial Advisor dashboard
- **API Docs**: Open http://localhost:8000/docs - Interactive API documentation
- **Health Check**: `curl http://localhost:8000/health` should return `{"status":"healthy"}`

<!-- ![Application - Dashboard home](docs/screenshots/app-dashboard-home.png) -->

<!-- ![FastAPI - Swagger docs](docs/screenshots/fastapi-docs.png) -->

---

### Step 7: Run Your First Investigation

Now let's use the multi-agent system to investigate a customer.

#### 7.1 Open the Chat Interface

In the application, click on **"AI Assistant"** in the sidebar to open the chat interface.

<!-- ![Application - Chat interface](docs/screenshots/app-chat-interface.png) -->

#### 7.2 Start an Investigation

Type a query like:

```
Investigate customer CUST-003 for potential money laundering risks
```

Press Enter and watch as the multi-agent system:

1. **Supervisor Agent** analyzes your request
2. **KYC Agent** verifies customer identity
3. **AML Agent** scans transaction patterns
4. **Relationship Agent** maps network connections
5. **Compliance Agent** checks sanctions lists

<!-- ![Application - Agent thinking](docs/screenshots/app-agent-thinking.png) -->

#### 7.3 Review the Results

The supervisor synthesizes all findings into a comprehensive report:

<!-- ![Application - Investigation results](docs/screenshots/app-investigation-results.png) -->

#### 7.4 Explore the Relationship Network

Click on **"Network Graph"** to visualize the customer's connections:

<!-- ![Application - Network visualization](docs/screenshots/app-network-graph.png) -->

---

### Step 8: Deploy to Google Cloud Run (Optional)

Ready to deploy to production? Follow these steps.

#### 8.1 Set Up Secrets

Store your Neo4j credentials securely:

```bash
# Create secrets
echo -n "neo4j+s://xxx.databases.neo4j.io" | \
  gcloud secrets create neo4j-uri --data-file=-

echo -n "your-neo4j-password" | \
  gcloud secrets create neo4j-password --data-file=-
```

#### 8.2 Deploy the Backend

```bash
cd backend

gcloud run deploy financial-advisor-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets NEO4J_URI=neo4j-uri:latest,NEO4J_PASSWORD=neo4j-password:latest \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,VERTEX_AI_LOCATION=us-central1
```

#### 8.3 Deploy the Frontend

```bash
cd frontend
npm run build

# Deploy to Cloud Storage + CDN, or Cloud Run
gcloud run deploy financial-advisor-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

<!-- ![Google Cloud Console - Cloud Run deployed](docs/screenshots/gcp-cloud-run-deployed.png) -->

---

## Troubleshooting

### "Permission denied" when accessing Vertex AI

Ensure you've authenticated and have the right roles:

```bash
gcloud auth application-default login
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/aiplatform.user"
```

### Neo4j connection refused

For local Neo4j, ensure Docker is running:

```bash
docker ps | grep neo4j
# If not running:
docker start neo4j
```

For Aura, verify your URI includes `neo4j+s://` (not `bolt://`).

### Frontend can't connect to backend

Check that CORS is configured correctly in `.env`:

```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### "Module not found" errors

Reinstall dependencies:

```bash
make clean
make install
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Google Cloud                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────────────────┐│
│  │  Cloud CDN   │───▶│    Cloud Run     │───▶│        Vertex AI           ││
│  │  (Frontend)  │    │ (FastAPI + ADK)  │    │  (Gemini + Embeddings)     ││
│  └──────────────┘    └──────────────────┘    └────────────────────────────┘│
│                               │                                              │
│         ┌─────────────────────┼──────────────────────┐                      │
│         ▼                     ▼                      ▼                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │Secret Manager│    │  Neo4j Aura  │    │Cloud Storage │                  │
│  │ (Credentials)│    │(Context Graph)│    │  (Documents) │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Multi-Agent System

```
                     ┌───────────────────┐
                     │ SupervisorAgent   │
                     │ (Coordinator)     │
                     └─────────┬─────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐
    │             │    │             │    │             │
┌───┴───┐    ┌───┴───┐    ┌─────────┴─┐    ┌─────────┐
│  KYC  │    │  AML  │    │Relationship│    │Compliance│
│ Agent │    │ Agent │    │   Agent    │    │  Agent   │
└───────┘    └───────┘    └────────────┘    └──────────┘
```

| Agent | Responsibility |
|-------|----------------|
| **Supervisor** | Orchestrates investigation workflow |
| **KYC Agent** | Identity verification, document checking |
| **AML Agent** | Transaction monitoring, pattern detection |
| **Relationship Agent** | Network analysis using Context Graph |
| **Compliance Agent** | Sanctions/PEP screening, report generation |

---

## Project Structure

```
google-cloud-financial-advisor/
├── backend/
│   ├── src/
│   │   ├── agents/        # Google ADK agent definitions
│   │   ├── tools/         # Agent tools (KYC, AML, etc.)
│   │   ├── api/routes/    # FastAPI endpoints
│   │   ├── models/        # Pydantic models
│   │   └── services/      # Memory service, risk service
│   ├── Dockerfile
│   └── pyproject.toml     # Dependencies managed with uv
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   └── lib/           # API client
│   └── package.json
├── infrastructure/        # Cloud Run deployment configs
├── data/                  # Sample data and loader
├── docs/                  # Documentation
├── Makefile              # Development commands
└── docker-compose.yml    # Local development setup
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message to AI advisor |
| `/api/chat/history/{session_id}` | GET | Get conversation history |
| `/api/customers` | GET | List customers |
| `/api/customers/{id}/risk` | GET | Risk assessment |
| `/api/customers/{id}/network` | GET | Relationship network |
| `/api/investigations` | POST | Create investigation |
| `/api/investigations/{id}/start` | POST | Start multi-agent investigation |
| `/api/investigations/{id}/audit-trail` | GET | Get reasoning trace |
| `/api/alerts` | GET | List compliance alerts |
| `/api/graph/stats` | GET | Graph statistics |

Full API documentation available at http://localhost:8000/docs when running locally.

---

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | Yes |
| `VERTEX_AI_LOCATION` | Vertex AI region (e.g., `us-central1`) | Yes |
| `VERTEX_AI_MODEL_ID` | Gemini model ID | Yes |
| `VERTEX_AI_EMBEDDING_MODEL` | Embedding model ID | Yes |
| `NEO4J_URI` | Neo4j connection URI | Yes |
| `NEO4J_USER` | Neo4j username | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `LOG_LEVEL` | Logging level | No (default: INFO) |
| `CORS_ORIGINS` | Allowed CORS origins | No |

---

## References

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Neo4j Agent Memory](https://github.com/neo4j-labs/agent-memory)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Neo4j Aura](https://neo4j.com/cloud/aura/)

## License

This example is part of the neo4j-agent-memory project and is licensed under the Apache 2.0 License.
