# Mavik AI - Multi-Agent Underwriting & Strategy System

A production-ready, end-to-end AI underwriting and strategy system built with Python (backend) and Next.js (web).

## Architecture Overview

- **Main LLM (Orchestrator)**: Routes to specialized agents (Originations, Strategy, XYZ)
- **MCP Tools**: RAG, Document Parser, Financial DB, Web Research, Calculator, Report Builder
- **AI Models**: AWS Bedrock with Anthropic Claude 3 Sonnet + Amazon Titan Text Embeddings v2
- **Data**: Aurora Postgres (RDS Proxy), DynamoDB audit, S3 with KMS, OpenSearch Serverless
- **Runtime**: ECS Fargate + Lambda
- **UI**: Next.js with streaming chat, tool tracing, and DOCX downloads
- **Security**: Private VPC, VPCEs, IAM least-privilege, KMS encryption, Guardrails

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Poetry
- pnpm
- AWS CLI configured

### Local Development (Mock Mode)

1. **Install dependencies**:
   ```bash
   # Python services
   poetry install

   # Web application
   cd apps/web && pnpm install
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   export MOCK_AWS=true
   ```

3. **Run the Orchestrator locally**
  - VS Code Task: open Command Palette → "Tasks: Run Task" → "Orchestrator"
  - VS Code Debug: Run and Debug panel → "Orchestrator (Uvicorn Debug)"
  - Terminal (optional): `poetry run uvicorn apps.orchestrator.main:app --reload --host 127.0.0.1 --port 8080`

4. **Smoke test the API**
  - Health: `curl http://127.0.0.1:8080/health`
  - Orchestrate: `curl -X POST http://127.0.0.1:8080/orchestrate -H "Content-Type: application/json" -d '{"message":"hello"}'`
  - Postman: import the two requests above; expect `{ "status":"ok" }` and an echo response with `agent_used: "pre-screening"`.

5. **Production LLM endpoint (AWS Bedrock)**
   - Configure environment:
     - `AWS_REGION` (or `AWS_DEFAULT_REGION`)
     - `BEDROCK_MODEL_ID` (default: anthropic.claude-3-5-sonnet-20240620-v1:0)
     - Optional: `BEDROCK_TEMPERATURE` (0.2), `BEDROCK_MAX_TOKENS` (2048), `BEDROCK_TOP_P` (0.9)
   - Call the endpoint:
     - `curl -X POST http://127.0.0.1:8080/chat -H "Content-Type: application/json" -d '{"message":"Summarize this system."}'`
   - If Bedrock is not configured, the endpoint returns HTTP 503 with an error detail.

6. **Run smoke tests**:
   ```bash
   python apps/smoke/smoke_orchestrator_local.py
   python apps/smoke/smoke_tools_local.py
   python apps/smoke/smoke_report_local.py
   ```

### Cloud Deployment

1. **Deploy infrastructure**:
   ```bash
   cd infra/cdk
   cdk deploy --all
   ```

2. **Build and push containers**:
   ```bash
   # CI/CD handles this automatically
   .github/workflows/deploy.yml
   ```

## Repository Structure

```
/apps
  /web                 # Next.js 14 app (chat UI, trace, citations, downloads)
  /orchestrator        # FastAPI service (MCP client, Bedrock streaming, routing)
  /smoke               # Python CLIs for local smoke tests (no curl/admin)
/services
  /mcp-rag             # FastAPI WebSocket JSON-RPC; OpenSearch+KB query
  /mcp-parser          # Textract + postprocessing; emits tables/text + confidence
  /mcp-findb           # Aurora (RDS Proxy) parameterized reads; ABAC filters
  /mcp-web             # Allowlisted web fetcher with DDB TTL cache
  /mcp-calc            # Deterministic IRR/NPV/DSCR with provenance
  /mcp-report          # Lambda (Python) → DOCX → S3 → presigned URL
/packages
  /common              # Shared pydantic models, JSON schemas, error types
  /aws_clients         # Thin clients for Bedrock/OpenSearch/S3/DDB/RDS
  /config              # Environment loader, flags (AppConfig-ready)
  /evals               # Evaluation harness + golden sets/fixtures
/infra/cdk             # CDK app + stacks
/.github/workflows     # CI/CD pipelines
/docs                  # ADRs, runbooks, security model, evals methodology
```

## Key Features

### Multi-Agent Architecture
- **Originations Agent**: Deal intake, pre-screening, comparables, rent rolls
- **Strategy Agent**: Portfolio analysis, mandate fit, macro trends
- **XYZ Agent**: Extensible for future capabilities

### MCP Tool Integration
- **RAG**: Hybrid vector + BM25 search with OpenSearch Serverless
- **Parser**: Textract-based document processing with confidence scoring
- **FinDB**: Financial metrics and KPI queries with ABAC
- **Web**: Research with allowlisted domains and credibility scoring
- **Calculator**: Financial computations (IRR, NPV, DSCR) with provenance
- **Reports**: DOCX generation with 1" margins and S3 storage

### Security & Compliance
- Private VPC with VPC endpoints for all AWS services
- KMS encryption for all data at rest
- IAM least-privilege with ABAC
- Bedrock Guardrails for content filtering
- Audit trail for all AI interactions

## Development

### Local Testing
All services run locally in MOCK_AWS mode for development:
- Uses SQLite instead of Aurora
- Local filesystem instead of S3
- In-memory search instead of OpenSearch
- Mock embeddings instead of Bedrock

### VS Code Integration
- Launch configurations for all services
- Tasks for common operations
- Integrated debugging support

### Quality Gates
- Automated testing (pytest, vitest, Playwright)
- Code quality (ruff, mypy, prettier)
- Security scanning (Trivy, Bandit)
- Performance benchmarks
- Evaluation harness with support-rate metrics

## Monitoring & Observability

- Structured logging with correlation IDs
- CloudWatch metrics and X-Ray tracing
- Cost tracking by user/agent/tool
- Performance dashboards
- Alerting for timeouts and anomalies

## Contributing

1. Create feature branch from `main`
2. Make changes with tests
3. Run smoke tests locally
4. Submit PR with evaluation results
5. Automated CI/CD on merge

## Documentation

- [Architecture Decision Records](docs/adrs/)
- [Security Model](docs/security.md)
- [Runbooks](docs/runbooks/)
- [Evaluation Methodology](docs/evals.md)

## License



<svg width="1400" height="980" viewBox="0 0 1400 980" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .box{fill:#ffffff;stroke:#2b2b36;stroke-width:2;rx:12;ry:12;}
      .faint{fill:#eef0f4;stroke:#a7adba;}
      .title{font:700 20px Inter,Arial,sans-serif;fill:#1f2430;}
      .label{font:600 14px Inter,Arial,sans-serif;fill:#1f2430;}
      .small{font:500 12px Inter,Arial,sans-serif;fill:#454b5e;}
      .legend{font:500 12px Inter,Arial,sans-serif;fill:#6b7280;}
      .cloud{fill:#f5f7fb;stroke:#9aa1b2;stroke-width:2;}
      .dash{stroke:#7a7f8a;stroke-width:2;stroke-dasharray:6 6;fill:none;}
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2b2b36"/>
    </marker>
  </defs>

  <!-- Title -->
  <text x="700" y="32" text-anchor="middle" class="title">Mavik AI — Production Architecture (In-Scope)</text>

  <!-- Clients -->
  <rect x="90" y="70" width="1220" height="70" class="faint" rx="14" ry="14"/>
  <text x="700" y="95" text-anchor="middle" class="label">Client Applications</text>

  <rect x="140" y="105" width="160" height="40" class="box"/>
  <text x="220" y="130" text-anchor="middle" class="small">Web App (Next.js)</text>

  <rect x="360" y="105" width="170" height="40" class="box" fill="#f0f1f5" stroke="#c6c9d1"/>
  <text x="445" y="130" text-anchor="middle" class="small" fill="#7c8191">Mobile App (future)</text>

  <rect x="570" y="105" width="170" height="40" class="box" fill="#f0f1f5" stroke="#c6c9d1"/>
  <text x="655" y="130" text-anchor="middle" class="small" fill="#7c8191">Power BI (future)</text>

  <!-- API Gateway -->
  <rect x="370" y="180" width="660" height="80" class="box"/>
  <text x="700" y="205" text-anchor="middle" class="label">API Gateway (REST + WebSocket)</text>
  <text x="700" y="225" text-anchor="middle" class="small">Auth: Cognito OIDC (default) • Lambda Authorizer (alt)</text>
  <text x="700" y="242" text-anchor="middle" class="small">Rate limiting • Logging • WAF</text>

  <!-- Connect clients to API GW -->
  <line x1="220" y1="145" x2="700" y2="180" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="445" y1="145" x2="700" y2="180" stroke="#a7adba" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="655" y1="145" x2="700" y2="180" stroke="#a7adba" stroke-width="2" marker-end="url(#arrow)"/>
  <text x="270" y="168" class="legend">HTTP/WebSocket</text>

  <!-- Orchestrator -->
  <rect x="320" y="290" width="760" height="110" class="box"/>
  <text x="700" y="315" text-anchor="middle" class="label">AI Orchestrator (Python FastAPI on ECS Fargate)</text>
  <text x="700" y="335" text-anchor="middle" class="small">Streams via Bedrock Claude 3 Sonnet • Routing • Budgets • Guardrails • Context Assembler</text>
  <text x="700" y="355" text-anchor="middle" class="small">Audit & Costs → DynamoDB • Errors & Fallbacks</text>

  <!-- Arrow API GW -> Orchestrator -->
  <line x1="700" y1="260" x2="700" y2="290" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <text x="710" y="275" class="legend">HTTP/WS</text>

  <!-- Guardrails -->
  <rect x="1100" y="305" width="180" height="60" class="box"/>
  <text x="1190" y="330" text-anchor="middle" class="small">Bedrock Guardrails</text>
  <line x1="1080" y1="335" x2="1100" y2="335" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Agents -->
  <text x="700" y="420" text-anchor="middle" class="legend">Specialist Agents (policies inside orchestrator)</text>
  <rect x="370" y="430" width="220" height="56" class="box"/>
  <text x="480" y="462" text-anchor="middle" class="small">Originations Agent</text>

  <rect x="640" y="430" width="220" height="56" class="box"/>
  <text x="750" y="462" text-anchor="middle" class="small">Strategy Agent</text>

  <rect x="910" y="430" width="220" height="56" class="box" fill="#f0f1f5" stroke="#c6c9d1"/>
  <text x="1020" y="462" text-anchor="middle" class="small" fill="#7c8191">XYZ Agent (disabled)</text>

  <!-- Orchestrator -> Agents arrows -->
  <line x1="700" y1="400" x2="480" y2="430" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="700" y1="400" x2="750" y2="430" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="700" y1="400" x2="1020" y2="430" stroke="#a7adba" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- MCP boundary -->
  <rect x="120" y="510" width="1160" height="210" class="dash"/>
  <text x="700" y="525" text-anchor="middle" class="legend">MCP Protocol Boundary (Orchestrator ⇄ Tool Servers)</text>

  <!-- MCP Servers -->
  <rect x="150" y="550" width="170" height="60" class="box"/>
  <text x="235" y="575" text-anchor="middle" class="small">RAG Server</text>
  <text x="235" y="592" text-anchor="middle" class="legend">OpenSearch+KB</text>

  <rect x="340" y="550" width="190" height="60" class="box"/>
  <text x="435" y="575" text-anchor="middle" class="small">Document Parser</text>
  <text x="435" y="592" text-anchor="middle" class="legend">Textract</text>

  <rect x="550" y="550" width="190" height="60" class="box"/>
  <text x="645" y="575" text-anchor="middle" class="small">Financial DB</text>
  <text x="645" y="592" text-anchor="middle" class="legend">Aurora (RDS Proxy)</text>

  <rect x="760" y="550" width="190" height="60" class="box"/>
  <text x="855" y="575" text-anchor="middle" class="small">Web Research</text>
  <text x="855" y="592" text-anchor="middle" class="legend">Allowlisted Egress</text>

  <rect x="970" y="550" width="160" height="60" class="box"/>
  <text x="1050" y="575" text-anchor="middle" class="small">Calc Tool</text>
  <text x="1050" y="592" text-anchor="middle" class="legend">IRR/DSCR/NPV</text>

  <rect x="1150" y="550" width="110" height="60" class="box"/>
  <text x="1205" y="575" text-anchor="middle" class="small">Report Builder</text>
  <text x="1205" y="592" text-anchor="middle" class="legend">DOCX→S3</text>

  <!-- Orchestrator -> MCP boundary arrow -->
  <line x1="700" y1="486" x2="700" y2="510" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <text x="710" y="500" class="legend">MCP</text>

  <!-- Data layer -->
  <rect x="160" y="750" width="200" height="70" class="box"/>
  <text x="260" y="775" text-anchor="middle" class="small">OpenSearch Serverless</text>
  <text x="260" y="793" text-anchor="middle" class="legend">Vector + BM25</text>

  <rect x="400" y="750" width="180" height="70" class="box"/>
  <text x="490" y="775" text-anchor="middle" class="small">S3 (KMS)</text>
  <text x="490" y="793" text-anchor="middle" class="legend">Raw/Curated/Reports</text>

  <rect x="610" y="750" width="200" height="70" class="box"/>
  <text x="710" y="775" text-anchor="middle" class="small">Aurora Postgres + Proxy</text>
  <text x="710" y="793" text-anchor="middle" class="legend">Deals & Metrics</text>

  <rect x="850" y="750" width="190" height="70" class="box"/>
  <text x="945" y="775" text-anchor="middle" class="small">DynamoDB (Audit/Costs)</text>
  <text x="945" y="793" text-anchor="middle" class="legend">Immutable stream → S3</text>

  <path d="M 1080 760
           C 1100 730, 1190 730, 1210 760
           C 1230 790, 1170 805, 1120 790
           C 1090 780, 1060 785, 1080 760 Z" class="cloud"/>
  <text x="1160" y="775" text-anchor="middle" class="small">Allowlisted Web</text>

  <!-- Tool -> Data connections -->
  <line x1="235" y1="610" x2="260" y2="750" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="435" y1="610" x2="490" y2="750" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="435" y1="610" x2="710" y2="750" stroke="#a7adba" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="645" y1="610" x2="710" y2="750" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="855" y1="610" x2="1140" y2="760" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="1205" y1="610" x2="490" y2="750" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Orchestrator -> DDB audit -->
  <line x1="820" y1="400" x2="945" y2="750" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/>
  <text x="890" y="565" class="legend">Audit & Costs</text>

  <!-- Legend -->
  <rect x="90" y="880" width="540" height="70" class="faint" rx="10" ry="10"/>
  <text x="110" y="905" class="legend">Legend:</text>
  <rect x="180" y="890" width="18" height="14" class="box"/><text x="205" y="901" class="legend">In-scope (now)</text>
  <rect x="320" y="890" width="18" height="14" class="box" fill="#f0f1f5" stroke="#c6c9d1"/><text x="345" y="901" class="legend">Future (grey)</text>
  <line x1="180" y1="930" x2="220" y2="930" stroke="#2b2b36" stroke-width="2" marker-end="url(#arrow)"/><text x="228" y="935" class="legend">HTTP/WebSocket</text>
  <line x1="360" y1="930" x2="400" y2="930" stroke="#2b2b36" stroke-width="2" stroke-dasharray="6 6" marker-end="url(#arrow)"/>
  <text x="408" y="935" class="legend">MCP boundary</text>
</svg>
