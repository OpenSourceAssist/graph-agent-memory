# Financial Services Advisor

An intelligent compliance assistant powered by **AWS Strands Agents** and **Neo4j Agent Memory Context Graphs**, demonstrating multi-agent AI for KYC/AML compliance, fraud detection, and relationship intelligence.

## Overview

This example application showcases the AWS-Neo4j partnership through a production-ready architecture for financial services compliance. It demonstrates how AI agents can leverage graph-based memory for explainable, auditable decision-making.

### Key Features

- **Multi-Agent Investigation**: Coordinated KYC, AML, relationship, and compliance analysis
- **Context Graph Intelligence**: Relationship mapping and network analysis with Neo4j
- **Explainable AI**: Full audit trails for regulatory compliance (EU AI Act ready)
- **Real-time Monitoring**: Transaction and behavior pattern detection
- **Graph-based RAG**: Reduces hallucinations through grounded, relationship-aware retrieval

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐  │
│  │  CloudFront  │───▶│ API Gateway  │───▶│      Lambda (FastAPI)        │  │
│  │  (Frontend)  │    │  + Cognito   │    │   + Strands Agent + Tools    │  │
│  └──────────────┘    └──────────────┘    └──────────────┬───────────────┘  │
│                                                          │                   │
│         ┌────────────────────────────────────────────────┼──────────────┐   │
│         │                                                │              │   │
│         ▼                                                ▼              ▼   │
│  ┌──────────────┐                              ┌──────────────┐  ┌────────┐│
│  │   Bedrock    │                              │  Neo4j Aura  │  │   S3   ││
│  │ Claude+Titan │                              │Context Graph │  │  Docs  ││
│  └──────────────┘                              └──────────────┘  └────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### AWS Services Highlighted

| Service | Role |
|---------|------|
| **Amazon Bedrock** | LLM (Claude) + Embeddings (Titan) |
| **AWS Lambda** | Serverless compute for API |
| **Amazon API Gateway** | REST API management |
| **Amazon CloudFront** | CDN for frontend |
| **Amazon Cognito** | Authentication |
| **Amazon CloudWatch** | Monitoring & logging |
| **Amazon S3** | Document storage |

### Multi-Agent System

| Agent | Responsibility |
|-------|----------------|
| **Supervisor** | Orchestrates investigation workflow |
| **KYC Agent** | Identity verification, document checking |
| **AML Agent** | Transaction monitoring, pattern detection |
| **Relationship Agent** | Network analysis using Context Graph |
| **Compliance Agent** | Sanctions/PEP screening, report generation |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- AWS CLI configured with Bedrock access
- Neo4j Aura account (or local Neo4j instance)

### Local Development

1. **Clone and navigate to the example:**

```bash
cd examples/financial-services-advisor
```

2. **Set up environment:**

```bash
cp .env.example .env
# Edit .env with your Neo4j and AWS credentials
```

3. **Install backend dependencies:**

```bash
cd backend
pip install -r requirements.txt
```

4. **Install frontend dependencies:**

```bash
cd ../frontend
npm install
```

5. **Load sample data:**

```bash
cd ../data
python load_sample_data.py
```

6. **Run the backend:**

```bash
cd ../backend
uvicorn src.main:app --reload
```

7. **Run the frontend:**

```bash
cd ../frontend
npm run dev
```

8. **Access the application:**
   - Frontend: http://localhost:5173
   - API Docs: http://localhost:8000/docs

### AWS Deployment

Deploy the complete stack using AWS CDK:

```bash
cd infrastructure
npm install
npm run cdk bootstrap  # First time only
npm run cdk deploy --all
```

## Project Structure

```
financial-services-advisor/
├── backend/
│   ├── src/
│   │   ├── agents/        # Strands Agent definitions
│   │   ├── api/routes/    # FastAPI endpoints
│   │   ├── models/        # Pydantic models
│   │   └── services/      # Business logic
│   ├── handler.py         # Lambda handler
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   └── lib/           # API client
│   └── package.json
├── infrastructure/        # AWS CDK stacks
├── data/                  # Sample data
└── docs/
    └── diagrams/          # Architecture diagrams
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Interact with the AI advisor |
| `/api/customers` | GET/POST | Customer management |
| `/api/customers/{id}/risk` | GET | Risk assessment |
| `/api/customers/{id}/network` | GET | Relationship network |
| `/api/investigations` | GET/POST | Investigation management |
| `/api/investigations/{id}/start` | POST | Start multi-agent investigation |
| `/api/investigations/{id}/audit-trail` | GET | Get reasoning trace |
| `/api/alerts` | GET | Compliance alerts |
| `/api/reports/sar` | POST | Generate SAR report |

## Memory Types

The application uses three types of Context Graph memory:

| Memory Type | Purpose | Example Use |
|-------------|---------|-------------|
| **Short-Term** | Conversation history | Chat context, session state |
| **Long-Term** | Entities & relationships | Customer profiles, org networks |
| **Reasoning** | Decision audit trails | Investigation traces, agent reasoning |

## Sample Investigation Flow

1. **User Request**: "Investigate customer CUST-003 for potential money laundering"

2. **Supervisor Agent**:
   - Analyzes the request
   - Delegates to specialized agents in parallel

3. **KYC Agent**: Verifies identity, checks documents
4. **AML Agent**: Scans transactions, detects patterns
5. **Relationship Agent**: Maps network connections via Context Graph
6. **Compliance Agent**: Screens against sanctions lists

5. **Supervisor Synthesis**:
   - Combines all findings
   - Generates risk assessment
   - Provides recommendations

6. **Audit Trail**: Complete reasoning trace stored in Neo4j

## Environment Variables

```bash
# Neo4j
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# AWS
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# App
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
```

## Security Considerations

- **Authentication**: Cognito with MFA for compliance users
- **Authorization**: Role-based access (Analyst, Supervisor, Admin)
- **Audit Trail**: All actions logged to CloudWatch and Context Graph
- **Data Encryption**: At-rest (S3, Neo4j) and in-transit (TLS)
- **PII Handling**: Tokenization for sensitive customer data

## Business Value

### For Financial Institutions
- **Faster Investigations**: Multi-agent parallel processing
- **Better Detection**: Graph-based relationship analysis
- **Regulatory Compliance**: Full audit trails for AI decisions
- **Reduced False Positives**: Context-aware risk assessment

### For AWS-Neo4j Partnership
- Demonstrates Bedrock + Strands for regulated industries
- Shows Context Graphs as essential AI memory layer
- Highlights serverless architecture for AI workloads
- Joint solution for EU AI Act requirements

## References

- [AWS Agentic AI in Financial Services](https://aws.amazon.com/blogs/industries/agentic-ai-in-financial-services/)
- [Neo4j + AWS Strategic Partnership](https://neo4j.com/press-releases/neo4j-aws-bedrock-integration/)
- [Strands Agents SDK](https://strandsagents.com/latest/)
- [Neo4j Agent Memory](https://github.com/neo4j-labs/agent-memory)

## License

This example is part of the neo4j-agent-memory project and is licensed under the Apache 2.0 License.
