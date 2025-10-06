# Mavik AI Pre-Screening Assistant

A ChatGPT-style AI assistant for commercial real estate deal analysis, powered by AWS Bedrock Claude and LangGraph.

## Features

- **Dynamic Routing**: Intelligently routes requests based on user intent
- **PDF Analysis**: Upload offering memorandums for comprehensive pre-screening
- **Q&A Mode**: Ask questions about CRE deals without uploading files
- **Financial Calculations**: Automatic DSCR, LTV, Cap Rate calculations with trail strings
- **Word Export**: Download structured analysis reports
- **Streaming Responses**: Real-time updates as the analysis progresses

## Architecture

```
Frontend (Next.js) → FastAPI Backend → LangGraph Orchestrator → MCP Tools
                                        ├── Doc Parser (AWS Textract)
                                        ├── RAG Search (OpenSearch)
                                        ├── Web Search (Tavily)
                                        ├── Finance Calculator
                                        └── Report Generator (Word)
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- AWS Account with Bedrock access
- AWS credentials configured

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd chat-assistant
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your AWS credentials and API keys
```

### 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd ../frontend
npm install
```

### 5. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
python run.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Open http://localhost:3000 in your browser.

**Note**: Make sure you have set up your AWS credentials in the `.env` file before running.

## Using Docker Compose

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Usage Examples

### 1. Full Pre-Screening with PDF

1. Upload an offering memorandum PDF
2. Paste the pre-screening prompt
3. Click "Send"
4. Wait for analysis (sections 0-10)
5. Download the Word document

### 2. Ask a Question

Simply type your question:
```
What are typical DSCR requirements for multifamily deals?
```

### 3. Calculate Metrics

```
Calculate DSCR for NOI of $2.5M and debt service of $1.8M
```

Response:
```
DSCR = 2,500,000 / 1,800,000 = 1.39x
```

## API Endpoints

### POST /api/chat

Main chat endpoint supporting both text and file uploads.

**Request (multipart/form-data):**
```
message: string (required)
file: PDF file (optional)
conversation_id: string (optional)
```

**Response (Server-Sent Events):**
```
event: tool
data: {"tool": "doc_parser", "status": "started"}

event: section
data: {"number": 0, "title": "Executive Summary", "content": "..."}

event: artifact
data: {"type": "docx", "url": "https://s3.../report.docx"}

event: done
data: {}
```

### GET /health

Health check endpoint.

## Testing

### Run Unit Tests

```bash
cd backend
pytest tests/test_mcp_tools.py -v
```

### Run Integration Tests

```bash
pytest tests/test_orchestrator.py -v
```

## Project Structure

```
chat-assistant/
├── backend/
│   ├── app.py                  # FastAPI application
│   ├── models.py               # Pydantic schemas
│   ├── bedrock_client.py       # AWS Bedrock wrapper
│   ├── orchestrator/
│   │   ├── graph.py            # LangGraph workflow
│   │   ├── router.py           # Intent classification
│   │   └── state.py            # State definitions
│   ├── mcp/                    # MCP tools
│   │   ├── doc_parser.py       # AWS Textract
│   │   ├── rag.py              # Vector search
│   │   ├── web.py              # Web search
│   │   ├── finance.py          # Calculations
│   │   ├── findb.py            # DB stub
│   │   └── report.py           # Word generator
│   ├── prompts/                # Prompt templates
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Main page
│   │   └── layout.tsx          # Root layout
│   ├── components/
│   │   ├── chat-interface.tsx  # Chat UI
│   │   └── message-list.tsx    # Messages
│   └── package.json
├── tests/
│   ├── test_mcp_tools.py
│   └── test_orchestrator.py
├── .env.example
├── docker-compose.yml
└── README.md
```

## Environment Variables

Required environment variables (see `.env.example`):

```bash
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# S3 Buckets
S3_BUCKET_UPLOADS=mavik-uploads
S3_BUCKET_REPORTS=mavik-reports

# Bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# OpenSearch (optional for RAG)
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200

# Tavily (for web search)
TAVILY_API_KEY=your_tavily_key
```

## Development

### Adding New Tools

1. Create tool in `backend/mcp/`
2. Add to orchestrator in `backend/orchestrator/graph.py`
3. Update intent classifier in `backend/orchestrator/router.py`

### Modifying Prompts

Edit prompt templates in `backend/prompts/`:
- `pre_screening.py` - Full OM analysis
- `system.py` - System instructions for Q&A

## Deployment

See [DEPLOY.md](./DEPLOY.md) for deployment instructions.

## Troubleshooting

### Backend won't start
- Check AWS credentials in `.env`
- Verify Python dependencies installed
- Check port 8000 is available

### Frontend won't connect
- Ensure backend is running on port 8000
- Check CORS settings in `backend/app.py`
- Verify frontend `.env.local` has correct backend URL

### PDF upload fails
- Check S3 bucket exists and is accessible
- Verify AWS credentials have S3 permissions
- Check file size (max 100MB recommended)

## Support

For issues and questions, please open a GitHub issue.

## License

Proprietary - Mavik Capital
