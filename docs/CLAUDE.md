Status: v1.0 Production-Ready
Owner: Development Team
Tool: Claude Code for end-to-end implementation
Purpose: Build a ChatGPT-style AI assistant for Mavik employees to analyze commercial real estate deals

WHAT YOU'RE BUILDING
A Claude-powered chat assistant that:

Accepts user prompts (with or without PDF uploads)
Dynamically routes to appropriate MCP tools based on intent
Returns structured analysis in Word format (when analyzing OMs)
Works like ChatGPT/Claude - clean, fast, intelligent

Key Principle: System must work whether user uploads PDF or just asks questions.

ARCHITECTURE
┌─────────────────────────────────────────────────────────┐
│  Frontend (Next.js - Claude/GPT style UI)               │
│  - Chat interface                                       │
│  - PDF upload                                           │
│  - Streaming responses                                  │
│  - Download artifacts (Word docs)                       │
└──────────────────┬──────────────────────────────────────┘
                   │ WebSocket/REST
┌──────────────────▼──────────────────────────────────────┐
│  Backend (FastAPI + LangGraph)                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Intent Classifier (Claude Haiku)               │   │
│  │  - Determines: pre-screen | research | calc     │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼──────────────────────────────────┐   │
│  │  LangGraph Orchestrator                         │   │
│  │  - Dynamic routing based on intent + inputs     │   │
│  │  - Parallel tool execution                      │   │
│  │  - State checkpointing                          │   │
│  └──────────────┬──────────────────────────────────┘   │
└─────────────────┼──────────────────────────────────────┘
                  │
    ┌─────────────┴─────────────┬─────────────┬──────────┐
    ▼                           ▼             ▼          ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│Doc      │  │RAG      │  │Web      │  │Finance  │  │Report   │
│Parser   │  │Search   │  │Search   │  │Calc     │  │Gen      │
│(Textract│  │(OpenSrch│  │(HTTP)   │  │(Python) │  │(docx)   │
└─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘

DYNAMIC ROUTING EXAMPLES
Scenario 1: Full OM Pre-Screen (with PDF)
User Input:
  Prompt: "Persona: You are a seasoned commercial real estate investment analyst..."
  File: Sunset_Apartments_OM.pdf

Orchestrator Route:
  1. doc_parser.extract(pdf) → get text + tables
  2. intent_classifier → "pre-screen"
  3. [rag.search, web.validate, finance.calc] → parallel execution
  4. claude_sonnet.synthesize → sections 0-10
  5. report.generate_docx → Word doc
  
Output: Streaming chat + downloadable Word document
Scenario 2: Research Question (no PDF)
User Input:
  Prompt: "What are typical DSCR requirements for multifamily deals?"

Orchestrator Route:
  1. intent_classifier → "research"
  2. rag.search("DSCR multifamily requirements")
  3. claude_sonnet.answer
  
Output: Chat response with citations
Scenario 3: Sponsor Research (no PDF)
User Input:
  Prompt: "Research Dapper Companies' track record in Las Vegas retail"

Orchestrator Route:
  1. intent_classifier → "research"
  2. web.search("Dapper Companies track record retail")
  3. rag.search("Dapper Companies past deals")
  4. claude_sonnet.synthesize
  
Output: Structured analysis with web citations
Scenario 4: Financial Calculation (no PDF)
User Input:
  Prompt: "Calculate DSCR for NOI of $2.5M and debt service of $1.8M"

Orchestrator Route:
  1. intent_classifier → "calculation"
  2. finance.calc("DSCR", {noi: 2500000, debt: 1800000})
  
Output: "DSCR = 2,500,000 / 1,800,000 = 1.39x"

TECH STACK

Backend: Python 3.11+, FastAPI, LangGraph, boto3
LLM: AWS Bedrock Claude Sonnet 4 (primary), Claude Haiku (routing)
Frontend: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
Tools:

AWS Textract (PDF extraction)
OpenSearch Serverless (RAG - stub for now)
HTTP requests (web search)
NumPy (finance calculations)
python-docx (Word generation)


Infrastructure: AWS Lambda, S3, DynamoDB (checkpoints)


REPOSITORY STRUCTURE
mavik-ai/
├── backend/
│   ├── app.py                          # FastAPI entry
│   ├── orchestrator.py                 # LangGraph workflow
│   ├── intent_classifier.py            # Routes based on user input
│   ├── tools/
│   │   ├── doc_parser.py              # AWS Textract
│   │   ├── rag.py                     # OpenSearch (stub)
│   │   ├── web.py                     # Web search
│   │   ├── finance.py                 # DSCR, LTV, IRR calcs
│   │   └── report.py                  # Word doc generator
│   ├── prompts/
│   │   ├── pre_screening.py           # Full pre-screen prompt
│   │   └── synthesis.py               # Section generation prompts
│   ├── models.py                      # Pydantic schemas
│   ├── requirements.txt
│   └── tests/
│       ├── test_orchestrator.py
│       ├── test_tools.py
│       └── test_with_real_pdf.py
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Landing page
│   │   ├── chat/
│   │   │   └── page.tsx              # Chat interface
│   │   └── api/
│   │       └── analyze/route.ts       # Backend proxy
│   ├── components/
│   │   ├── chat-interface.tsx
│   │   ├── message-list.tsx
│   │   ├── pdf-uploader.tsx
│   │   └── artifact-download.tsx
│   ├── lib/
│   │   └── api-client.ts
│   └── package.json
│
├── tests/
│   ├── postman/
│   │   └── Mavik_AI.postman_collection.json
│   └── sample_data/
│       ├── Sunset_Apartments_OM.pdf
│       └── test_prompts.txt
│
├── .env.example
├── README.md
└── CONTRACT.md                         # This file

API CONTRACTS
POST /api/analyze (Main endpoint)
Request (multipart/form-data or JSON):
json{
  "message": "Persona: You are a seasoned commercial real estate...",
  "file": <binary PDF> (optional),
  "session_id": "uuid",
  "user_id": "vince@mavik.com"
}
Response (Server-Sent Events stream):
event: status
data: {"message": "Classifying intent..."}

event: status
data: {"message": "Extracting PDF with Textract..."}

event: status
data: {"message": "Searching comparable deals..."}

event: section
data: {"number": 0, "title": "Executive Summary", "content": "..."}

event: section
data: {"number": 1, "title": "Sponsor Analysis", "content": "..."}

event: artifact
data: {"type": "docx", "url": "https://s3.../prescreen.docx", "label": "Pre-Screen Report"}

event: done
data: {"session_id": "uuid", "total_time_ms": 45000}

OUTPUT SPECIFICATIONS
When Analyzing OM (Sections 0-10)
Format: Word document with 1" margins, following Document 8 exactly.
Required Sections:

Executive Summary

1 paragraph overview
Top 3 reasons to pursue
Top 3 reasons to pass
Recommendation: ✅ Pursue | ⚠️ Flag | ❌ Pass


Sponsor Analysis

Identity and background
Track record (deals, geographies, performance)
Web citations for validation
Red flags (litigation, foreclosures)


Market & Submarket Analysis

Location, demographics
Employment drivers
Market cycle positioning
Rent growth trends with comparables


Competitive Set & Positioning

3-5 comparable properties
Rent, occupancy, amenities comparison
Pricing competitiveness


Business Plan Viability

Strategy (value-add, lease-up, etc.)
Renovation scope and budget
Stress test scenarios:

Rent growth 1% lower
Exit cap 50bps higher
Renovation cost overrun 10%




Financial Underwriting

SF, cost basis, value PSF
NOI (T12 vs Pro Forma)
Cap rate, IRR, equity multiple
DSCR, debt yield, cash-on-cash
All calculations with trail strings


Debt Structure & Financing Risk

LTV, LTC, interest rate, term
DSCR scenarios (base + downside)
Refinance/balloon risk


Legal, Regulatory & ESG

Zoning, entitlements
Rent control, tenant protections
Environmental risks


Risk Factors & Red Flags

Deal killers
Construction/lease-up/market concerns
Devil's advocate view


Investment Fit & Strategy Alignment

Core-plus vs value-add vs opportunistic
Institutional suitability


Scoring & Recommendation

Score: 0-100
Rationale
Final: ✅ Pursue | ⚠️ Flag | ❌ Pass



Finance Trail String Format:
DSCR = 4,005,426 / 2,970,000 = 1.35x
LTV = 31,500,000 / 42,000,000 = 75.0%
Cap Rate = 2,500,000 / 42,000,000 = 5.95%
When Answering Questions (No PDF)
Format: Markdown response with:

Clear answer
Supporting data/calculations
Citations (if web/RAG used)
Follow-up suggestions


LANGRAPH STATE & WORKFLOW
State Definition
pythonfrom typing import TypedDict, Optional, List, Dict

class AnalysisState(TypedDict):
    # Input
    message: str
    file_path: Optional[str]
    session_id: str
    user_id: str
    
    # Intent
    intent: str  # "pre-screen" | "research" | "calculation" | "general"
    has_pdf: bool
    
    # Extracted Data
    pdf_text: Optional[str]
    tables: Optional[List[Dict]]
    sponsor_name: Optional[str]
    
    # Tool Results
    rag_results: Dict
    web_results: Dict
    finance_results: Dict
    
    # Output
    sections: Dict[str, str]  # "0_executive": "...", etc.
    answer: Optional[str]      # For non-PDF queries
    citations: List[Dict]
    artifacts: List[Dict]      # Word docs, etc.
    
    # Metadata
    total_time_ms: int
    cost_usd: float
Workflow Graph
python# Conditional routing based on intent + inputs

START 
  → classify_intent
  → [Decision Node]
      IF intent == "pre-screen" AND has_pdf:
          → extract_pdf
          → extract_sponsor
          → [rag_search, web_validate, finance_calc] (parallel)
          → generate_sections (Claude Sonnet)
          → create_docx
          → END
      
      ELIF intent == "research":
          → [rag_search, web_validate] (parallel)
          → generate_answer (Claude Sonnet)
          → END
      
      ELIF intent == "calculation":
          → finance_calc
          → generate_answer
          → END
      
      ELSE:
          → generate_answer (Claude Sonnet)
          → END

TOOL SPECIFICATIONS
1. doc_parser (AWS Textract)
pythonasync def extract_pdf(file_path: str) -> Dict:
    """Extract text and tables from PDF using AWS Textract"""
    # Use synchronous Textract for PDFs < 100 pages
    # Returns: {"text": str, "tables": List[Dict], "pages": int}
2. rag (OpenSearch - STUB)
pythonasync def search_rag(query: str, top_k: int = 5) -> Dict:
    """Search past deals and market data"""
    # Returns: {"chunks": [{"text": str, "score": float, "source": str}]}
    # FOR NOW: Return empty results
3. web (HTTP Search)
pythonasync def validate_web(queries: List[str]) -> Dict:
    """Web search for sponsor validation"""
    # Use requests library with allowlist
    # Returns: {"results": [{"title": str, "url": str, "snippet": str}]}
4. finance (NumPy Calculations)
pythondef calculate_metrics(data: Dict) -> Dict:
    """
    Calculate: DSCR, LTV, LTC, Cap Rate, Debt Yield, IRR, Equity Multiple
    Always return trail strings
    """
    # Example:
    # {"dscr": {"value": 1.35, "trail": "DSCR = 4,005,426 / 2,970,000 = 1.35x"}}
5. report (python-docx)
pythonasync def generate_docx(sections: Dict, title: str) -> str:
    """Generate Word doc with 1" margins, return S3 URL"""
    # Use python-docx with proper styling
    # Upload to S3, return presigned URL

ENVIRONMENT VARIABLES
bash# .env.example

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_UPLOADS=mavik-uploads
S3_BUCKET_REPORTS=mavik-reports

# Bedrock
BEDROCK_MODEL_HAIKU=anthropic.claude-3-5-haiku-20241022-v1:0
BEDROCK_MODEL_SONNET=anthropic.claude-sonnet-4-20250514-v1:0

# OpenSearch (stub for now)
OPENSEARCH_ENDPOINT=
OPENSEARCH_INDEX=mavik-deals

# App
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
LOG_LEVEL=INFO

TESTING STRATEGY (TDD)
Unit Tests
python# backend/tests/test_tools.py
def test_finance_calc_dscr():
    result = calculate_metrics({
        "noi": 4005426,
        "debt_service": 2970000
    })
    assert result["dscr"]["value"] == 1.35
    assert "4,005,426 / 2,970,000" in result["dscr"]["trail"]

def test_pdf_extraction():
    # Use sample PDF
    result = await extract_pdf("tests/sample.pdf")
    assert "text" in result
    assert len(result["text"]) > 100
Integration Tests
python# backend/tests/test_orchestrator.py
async def test_full_prescreen_flow():
    state = {
        "message": "Analyze this OM...",
        "file_path": "tests/Sunset_Apartments_OM.pdf",
        "session_id": "test-123"
    }
    
    result = await run_orchestrator(state)
    
    assert result["intent"] == "pre-screen"
    assert "0_executive" in result["sections"]
    assert len(result["artifacts"]) > 0
    assert result["artifacts"][0]["type"] == "docx"
Postman Tests (Manual UAT)
Collection: Mavik AI Tests

Test 1: Full Pre-Screen with PDF
  POST /api/analyze
  Body: 
    - message: [Full persona prompt]
    - file: Sunset_Apartments_OM.pdf
  Expected: SSE stream with sections 0-10 + docx URL

Test 2: Research Question
  POST /api/analyze
  Body:
    - message: "What are typical DSCR requirements?"
  Expected: Answer with citations

Test 3: Calculation
  POST /api/analyze
  Body:
    - message: "Calculate DSCR for NOI $2.5M, debt service $1.8M"
  Expected: "DSCR = 2,500,000 / 1,800,000 = 1.39x"

ACCEPTANCE CRITERIA
Functional Requirements

 System accepts prompts with or without PDF
 Dynamic routing based on intent classification
 Processes 60-page PDFs within 60 seconds
 Returns sections 0-10 in exact order (for pre-screens)
 Finance calculations include trail strings
 Web citations included for sponsor validation
 Generates Word docs with 1" margins
 Handles missing data gracefully (no hallucinations)

Quality Requirements

 Unit test coverage ≥ 80%
 Integration tests pass
 Postman tests pass
 Response time < 60s for full pre-screen
 Response time < 10s for simple questions
 No crashes on malformed inputs

UI Requirements

 Chat interface looks like Claude/ChatGPT
 Streaming responses show in real-time
 PDF upload works (drag & drop)
 Download button for Word docs
 Mobile responsive


DEVELOPMENT WORKFLOW
Step 1: Backend Core (Day 1-2)
bash# Use Claude Code to generate:
1. backend/models.py - Pydantic schemas
2. backend/tools/ - All 5 tools with real implementations
3. backend/intent_classifier.py
4. backend/orchestrator.py - LangGraph workflow
5. backend/app.py - FastAPI with SSE streaming
Step 2: Testing (Day 2)
bash# Use Claude Code to generate:
1. backend/tests/test_tools.py
2. backend/tests/test_orchestrator.py
3. tests/postman/collection.json
Step 3: Frontend (Day 3)
bash# Use Claude Code to generate:
1. frontend/app/chat/page.tsx - Main UI
2. frontend/components/ - All React components
3. frontend/lib/api-client.ts - Backend integration
Step 4: Integration & UAT (Day 4)
bash# Manual testing with real PDFs
# Smoke test all scenarios
# Fix bugs, iterate

HOW TO USE THIS CONTRACT WITH CLAUDE CODE
Initial Setup
bash# 1. Create new project
mkdir mavik-ai && cd mavik-ai

# 2. Copy this CONTRACT.md into the project root

# 3. Open in VS Code with Claude Code extension

# 4. Run this prompt:
Claude Code Prompt:
I have a CONTRACT.md that specifies a complete system. Please:

1. Read CONTRACT.md thoroughly
2. Create the exact repository structure specified
3. Implement all backend code (app.py, orchestrator.py, tools/, models.py)
4. Write unit tests for all tools
5. Create integration tests for the orchestrator
6. Generate a Postman collection for manual testing
7. Ask me for confirmation before implementing frontend

Focus on production-ready code with:
- Proper error handling
- Type hints (Python) / TypeScript types
- Docstrings for all functions
- No mock/stub implementations except for RAG (OpenSearch)

After each major component, ask if I want to test before proceeding.
Iterative Development
After Claude Code generates backend:
Now let's test the backend:
1. Show me how to run it locally
2. Generate a test script I can run to verify all tools work
3. Create a Postman request for the full pre-screen scenario
After backend is verified:
Now implement the frontend:
1. Create Next.js chat interface matching the API contracts
2. Include streaming SSE support
3. Add PDF upload with drag & drop
4. Style it to look like Claude/ChatGPT

POSTMAN TESTING GUIDE
Setup

Import tests/postman/Mavik_AI.postman_collection.json
Set environment variable: base_url = http://localhost:8000
Upload sample PDF to tests/sample_data/

Test Scenarios
Test 1: Full Pre-Screen (with PDF)
POST {{base_url}}/api/analyze
Headers:
  Content-Type: multipart/form-data

Body (form-data):
  message: [Paste full prompt from Document 8]
  file: [Upload Sunset_Apartments_OM.pdf]

Expected:
  - SSE stream
  - Events: status, section (x11), artifact, done
  - Final artifact has docx URL
Test 2: Research Question (no PDF)
POST {{base_url}}/api/analyze
Headers:
  Content-Type: application/json

Body (JSON):
{
  "message": "What are typical DSCR requirements for multifamily deals?",
  "session_id": "test-research-123"
}

Expected:
  - Answer with explanation
  - RAG citations (if any)
  - No docx artifact
Test 3: Calculation (no PDF)
POST {{base_url}}/api/analyze
Headers:
  Content-Type: application/json

Body (JSON):
{
  "message": "Calculate DSCR for NOI of $2,500,000 and debt service of $1,800,000",
  "session_id": "test-calc-456"
}

Expected:
  - Answer: "DSCR = 2,500,000 / 1,800,000 = 1.39x"
  - Trail string included

SUCCESS METRICS
MVP Demo-Ready Checklist:

 Can process real OM PDF and return Word doc
 Can answer questions without PDF
 Can perform financial calculations
 UI looks professional (Claude/GPT style)
 All Postman tests pass
 Response times acceptable (< 60s full, < 10s simple)
 No crashes on edge cases


NOTES FOR DEVELOPER
Do NOT:

Build separate agent services (keep it simple)
Implement Paul's DB integration yet (stub it)
Add authentication/RBAC for MVP (focus on functionality)
Overcomplicate the orchestrator (dynamic routing is sufficient)

DO:

Follow the contract exactly
Use Claude Code to generate complete implementations
Test after each component
Keep code production-ready (no TODOs, no placeholders)
Focus on the core flow working end-to-end

When Stuck:

Re-read the relevant section of this contract
Ask Claude Code: "According to CONTRACT.md section X, how should I implement Y?"
Test with Postman before moving to next component