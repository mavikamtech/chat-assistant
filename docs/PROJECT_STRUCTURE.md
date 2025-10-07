# Chat Assistant Project Structure

```
chat-assistant/
├── README.md                    # Main project documentation
├── CLAUDE.md                    # Claude Code instructions for development
├── Test.md                      # UAT test plan and test cases
├── .env.example                 # Example environment variables
├── .gitignore                   # Git ignore rules
├── docker-compose.yml           # Docker configuration
│
├── docs/                        # Documentation
│   ├── AWS_SETUP.md            # AWS configuration guide
│   ├── PDF_UPLOAD_FIX.md       # PDF upload troubleshooting
│   ├── QUICKSTART.md           # Quick start guide
│   ├── RUNNING.md              # How to run the application
│   ├── SETUP_COMPLETE.md       # Setup completion checklist
│   ├── STATUS.md               # Project status
│   └── PDF_PARSING_TEST_RESULTS.md  # Test results documentation
│
├── backend/                     # FastAPI backend
│   ├── app.py                  # Main FastAPI application
│   ├── bedrock_client.py       # AWS Bedrock client (Claude integration)
│   ├── models.py               # Pydantic data models
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Environment variables (not in git)
│   │
│   ├── mcp/                    # MCP Servers (Tool implementations)
│   │   ├── doc_parser.py      # AWS Textract PDF extraction
│   │   ├── rag.py             # Vector search (OpenSearch)
│   │   ├── web.py             # Tavily web search
│   │   ├── finance.py         # Financial calculations
│   │   └── report.py          # Word document generation
│   │
│   ├── orchestrator/           # LangGraph workflow
│   │   ├── __init__.py
│   │   ├── state.py           # State definition
│   │   ├── router.py          # Intent classification
│   │   └── graph.py           # Workflow graph and nodes
│   │
│   ├── prompts/                # LLM prompts
│   │   ├── pre_screening.py   # Pre-screening analysis prompts
│   │   └── system.py          # System instructions
│   │
│   ├── tests/                  # Test scripts
│   │   ├── test_doc_parser_standalone.py    # Test Textract MCP
│   │   ├── test_case_c_extraction.py        # Test Case C (extraction)
│   │   ├── test_case_a_prescreening.py      # Test Case A (pre-screening)
│   │   ├── test_pdf_flow.py                 # Basic PDF flow test
│   │   ├── test_pdf_detailed.py             # Detailed PDF test
│   │   ├── test_end_to_end.py               # Full E2E test
│   │   └── test_s3_textract.py              # S3 + Textract test
│   │
│   └── scripts/                # Utility scripts
│       └── fix_s3_permissions.py  # S3 permission fixer
│
├── frontend/                    # Next.js frontend
│   ├── package.json            # Node dependencies
│   ├── next.config.js          # Next.js configuration
│   ├── tailwind.config.js      # Tailwind CSS config
│   │
│   ├── app/                    # Next.js app router
│   │   ├── page.tsx           # Landing page
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Global styles
│   │
│   ├── components/             # React components
│   │   ├── chat-interface.tsx # Main chat UI
│   │   ├── message-list.tsx   # Message display
│   │   └── pdf-uploader.tsx   # PDF upload component
│   │
│   └── lib/                    # Utilities
│       └── api-client.ts      # Backend API client
│
└── tests/                       # Integration tests
    └── scripts/                # Test automation scripts
```

## Key Files

### Backend
- **app.py** - FastAPI server with `/api/chat` endpoint
- **bedrock_client.py** - Manages Claude Sonnet v2 + Haiku models
- **orchestrator/graph.py** - Main workflow orchestration with LangGraph

### MCP Servers
- **doc_parser.py** - Extracts text + tables from PDFs using AWS Textract
- **web.py** - Searches web using Tavily API
- **finance.py** - Performs CRE financial calculations
- **report.py** - Generates Word documents

### Frontend
- **components/chat-interface.tsx** - Main chat UI with PDF upload
- **app/page.tsx** - Landing page

### Tests
- **test_case_c_extraction.py** - Tests simple data extraction
- **test_case_a_prescreening.py** - Tests full pre-screening analysis

## Running the Application

### Backend
```bash
cd backend
python app.py  # Runs on port 8000
```

### Frontend
```bash
cd frontend
npm run dev    # Runs on port 3000
```

### Tests
```bash
cd backend
python tests/test_case_c_extraction.py
python tests/test_case_a_prescreening.py
```

## Environment Setup

1. Copy `.env.example` to `backend/.env`
2. Fill in AWS credentials, Bedrock model IDs, Tavily API key
3. Ensure AWS Bedrock model access is granted

See `docs/QUICKSTART.md` for detailed setup instructions.
