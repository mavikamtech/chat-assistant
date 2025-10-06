# Orchestration & Routing Explained

## Overview
This application uses **LangGraph** to orchestrate a multi-step workflow that intelligently routes user requests to different processing paths based on intent classification. Think of it as a smart traffic controller that decides how to handle each user request.

---

## Architecture Diagram

```
User Request (Frontend)
        |
        v
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                    (app.py: /api/chat)                      │
└──────────────────┬──────────────────────────────────────────┘
                   |
                   v
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Orchestrator                         │
│              (orchestrator/graph.py)                        │
│                                                             │
│  START → classify_intent → [Decision Node] → tools → END   │
└─────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Flow

### 1. **User Sends Request** (Frontend → Backend)
**File:** `frontend/components/chat-interface.tsx`

```typescript
// User types message and optionally attaches PDF
const formData = new FormData();
formData.append('message', input);
if (file) formData.append('file', file);

// POST to backend
fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  body: formData,
});
```

**What happens:**
- User message + optional PDF file sent to backend
- Backend receives: `{ message: string, file?: File }`

---

### 2. **Backend Receives Request** (FastAPI)
**File:** `backend/app.py` (Lines ~100-150)

```python
@app.post("/api/chat")
async def chat(
    message: str = Form(...),
    file: UploadFile = File(None)
):
    # 1. Upload PDF to S3 (if provided)
    file_url = None
    if file:
        file_url = await upload_to_s3(file)

    # 2. Initialize orchestrator state
    initial_state = {
        "user_message": message,
        "file_url": file_url,
        "tool_calls": [],
        "selected_tools": []
    }

    # 3. Run LangGraph workflow
    async for state in run_orchestrator_streaming(initial_state):
        # Stream results back to frontend
        yield f"data: {json.dumps(state)}\n\n"
```

**What happens:**
- PDF uploaded to S3 (if provided)
- Initial state created with user message and file URL
- LangGraph orchestrator started

---

### 3. **LangGraph Orchestrator Starts** (The Brain)
**File:** `backend/orchestrator/graph.py` (Lines ~397-450)

The orchestrator is a **state machine** built with LangGraph:

```python
def create_graph():
    workflow = StateGraph(OrchestratorState)

    # Define all processing nodes
    workflow.add_node("classify", classify_intent)
    workflow.add_node("extract_pdf", extract_pdf)
    workflow.add_node("search_rag", search_rag)
    workflow.add_node("search_web", search_web)
    workflow.add_node("calculate", calculate_finance)
    workflow.add_node("generate", generate_response)
    workflow.add_node("create_docx", create_docx)

    # Define the flow
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "extract_pdf")
    workflow.add_edge("extract_pdf", "search_rag")
    workflow.add_edge("search_rag", "search_web")
    workflow.add_edge("search_web", "calculate")
    workflow.add_edge("calculate", "generate")
    workflow.add_edge("generate", "create_docx")
    workflow.add_edge("create_docx", END)

    return workflow.compile()
```

**What happens:**
- Creates a directed graph where each node is a processing step
- State flows from START → classify → extract_pdf → ... → END
- Each node can read/modify the shared state

---

### 4. **Intent Classification** (Router)
**File:** `backend/orchestrator/router.py`

This is the **traffic controller** - it decides which path to take:

```python
async def classify_intent(state: OrchestratorState) -> OrchestratorState:
    message_lower = state['user_message'].lower()

    # CASE 1: Explicit pre-screening request
    if state.get('file_url') and any(keyword in message_lower for keyword in [
        'pre-screen', 'full analysis', 'analyze this om'
    ]):
        intent = "pre_screen"
        selected_tools = ["doc_parser", "rag", "web", "finance", "report"]

    # CASE 2: PDF attached but asking specific question
    elif state.get('file_url'):
        intent = "document_qa"
        selected_tools = ["doc_parser"]

    # CASE 3: Research question (no PDF)
    elif any(keyword in message_lower for keyword in ['latest', 'current']):
        intent = "research"
        selected_tools = ["web"]

    # CASE 4: Calculation request
    elif any(keyword in message_lower for keyword in ['calculate', 'dscr', 'ltv']):
        intent = "calculation"
        selected_tools = ["finance"]

    # CASE 5: General question
    else:
        intent = "question"
        selected_tools = []

    state["intent"] = intent
    state["selected_tools"] = selected_tools
    return state
```

**What happens:**
- Analyzes user message and presence of PDF
- Decides intent: `pre_screen` | `document_qa` | `research` | `calculation` | `question`
- Selects which tools to run: `doc_parser`, `rag`, `web`, `finance`, `report`

---

### 5. **Tool Execution** (Conditional)
Each tool only runs if it's in `selected_tools`:

#### **A. Document Parser** (AWS Textract)
**File:** `backend/orchestrator/graph.py` (Lines ~11-40)

```python
async def extract_pdf(state: OrchestratorState) -> OrchestratorState:
    if not state.get("file_url"):
        return state  # Skip if no PDF

    # Extract text and tables from PDF using AWS Textract
    result = await doc_parser.extract_pdf_text(state["file_url"])

    state["pdf_text"] = result["text"]
    state["pdf_tables"] = result["tables"]
    return state
```

**What happens:**
- Only runs if PDF was uploaded
- Uses AWS Textract to extract text + tables from PDF
- Stores extracted content in state

---

#### **B. RAG Search** (Vector Database)
**File:** `backend/orchestrator/graph.py` (Lines ~42-70)

```python
async def search_rag(state: OrchestratorState) -> OrchestratorState:
    if "rag" not in state.get("selected_tools", []):
        return state  # Skip if not selected

    # Search for comparable deals in vector DB
    results = await rag.search(state["user_message"])
    state["rag_results"] = results
    return state
```

**What happens:**
- Only runs if `selected_tools` includes "rag"
- Searches vector database for similar past deals (currently stubbed)

---

#### **C. Web Search** (Tavily AI)
**File:** `backend/orchestrator/graph.py` (Lines ~72-100)

```python
async def search_web(state: OrchestratorState) -> OrchestratorState:
    if "web" not in state.get("selected_tools", []):
        return state

    # Perform web search for current information
    results = await web.search(state["user_message"])
    state["web_results"] = results
    return state
```

**What happens:**
- Only runs if `selected_tools` includes "web"
- Searches the web for real-time information (sponsor validation, market data)

---

#### **D. Finance Calculator**
**File:** `backend/orchestrator/graph.py` (Lines ~157-190)

```python
async def calculate_finance(state: OrchestratorState) -> OrchestratorState:
    if "finance" not in state.get("selected_tools", []):
        return state

    # Calculate financial metrics (DSCR, LTV, Cap Rate, etc.)
    calcs = await finance.calculate_metrics(state["pdf_text"])
    state["finance_calcs"] = calcs
    return state
```

**What happens:**
- Only runs if `selected_tools` includes "finance"
- Calculates metrics like DSCR, LTV, Cap Rate with trail strings

---

### 6. **Response Generation** (Claude)
**File:** `backend/orchestrator/graph.py` (Lines ~192-217)

```python
async def generate_response(state: OrchestratorState) -> OrchestratorState:
    intent = state.get("intent", "question")

    if intent == "pre_screen":
        # Full analysis - use all collected data
        prompt = build_pre_screening_prompt(state)
        full_response = await invoke_claude(prompt, SYSTEM_INSTRUCTIONS)
        state["answer"] = full_response

    elif intent == "document_qa":
        # Answer specific question about the PDF
        prompt = build_document_qa_prompt(state)
        state["answer"] = await invoke_claude(prompt, QA_SYSTEM_PROMPT)

    else:
        # General Q&A
        prompt = build_qa_prompt(state)
        state["answer"] = await invoke_claude(prompt, QA_SYSTEM_PROMPT)

    return state
```

**What happens:**
- Builds prompt based on intent
- Includes all gathered data: PDF text, tables, web results, RAG results, calculations
- Calls Claude Sonnet via AWS Bedrock
- Claude generates natural language response

---

### 7. **Document Creation** (Optional)
**File:** `backend/orchestrator/graph.py` (Lines ~222-256)

```python
async def create_docx(state: OrchestratorState) -> OrchestratorState:
    if state.get("intent") != "pre_screen":
        return state  # Only for full pre-screening

    # Generate Word document from analysis
    docx_url = await report.generate_docx(
        sections=state["sections"],
        title="Pre-Screening Analysis"
    )
    state["docx_url"] = docx_url
    return state
```

**What happens:**
- Only runs for `pre_screen` intent
- Generates downloadable Word document with analysis
- Uploads to S3, returns presigned URL

---

### 8. **Streaming Response to Frontend**
**File:** `backend/app.py`

```python
async for state in run_orchestrator_streaming(initial_state):
    # As each tool completes, stream update to frontend
    if state.get("answer"):
        yield f"data: {json.dumps({'type': 'answer', 'content': state['answer']})}\n\n"

    if state.get("docx_url"):
        yield f"data: {json.dumps({'type': 'artifact', 'url': state['docx_url']})}\n\n"
```

**What happens:**
- Results streamed to frontend as they're generated
- Frontend updates UI in real-time

---

## Intent Examples

### Example 1: "What is the DSCR?" (with PDF)
```
1. classify_intent() → intent = "document_qa", tools = ["doc_parser"]
2. extract_pdf() → Extracts text from PDF
3. search_rag() → SKIPPED (not in tools)
4. search_web() → SKIPPED (not in tools)
5. calculate() → SKIPPED (not in tools)
6. generate_response() → Calls Claude with PDF content + question
7. create_docx() → SKIPPED (not pre_screen intent)

Result: "The DSCR is 1.35x based on the financial data..."
```

---

### Example 2: "Give me a full analysis" (with PDF)
```
1. classify_intent() → intent = "pre_screen", tools = ["doc_parser", "rag", "web", "finance", "report"]
2. extract_pdf() → Extracts 59,192 chars + 51 tables
3. search_rag() → Searches for comparable deals
4. search_web() → Validates sponsor, market data
5. calculate() → Calculates DSCR, LTV, Cap Rate, etc.
6. generate_response() → Claude generates comprehensive analysis
7. create_docx() → Creates Word document

Result: Full markdown analysis + downloadable .docx
```

---

### Example 3: "What are typical LTV requirements?" (no PDF)
```
1. classify_intent() → intent = "question", tools = []
2. extract_pdf() → SKIPPED (no PDF)
3. search_rag() → SKIPPED (not in tools)
4. search_web() → SKIPPED (not in tools)
5. calculate() → SKIPPED (not in tools)
6. generate_response() → Claude answers from knowledge
7. create_docx() → SKIPPED (not pre_screen)

Result: "Typical LTV requirements for multifamily deals range from 65-75%..."
```

---

## State Management

**File:** `backend/orchestrator/state.py`

The state is a Python dictionary that flows through all nodes:

```python
class OrchestratorState(TypedDict):
    # Input
    user_message: str
    file_url: Optional[str]
    session_id: str

    # Intent & Routing
    intent: str  # "pre_screen" | "document_qa" | "research" | "calculation" | "question"
    selected_tools: List[str]

    # Extracted Data
    pdf_text: Optional[str]
    pdf_tables: Optional[List[Dict]]

    # Tool Results
    rag_results: List[Dict]
    web_results: List[Dict]
    finance_calcs: Dict

    # Output
    answer: Optional[str]
    docx_url: Optional[str]
    tool_calls: List[Dict]
```

Each node can:
- **Read** from state (e.g., `state["user_message"]`)
- **Write** to state (e.g., `state["pdf_text"] = extracted_text`)
- State is preserved across all nodes

---

## Key Design Decisions

### 1. **Conditional Tool Execution**
Tools only run if they're in `selected_tools`. This makes the system efficient:
- Simple questions skip PDF extraction, web search, etc.
- Full analysis runs all tools in parallel where possible

### 2. **Intent-Based Routing**
The router (`classify_intent`) decides the processing path:
- **pre_screen**: Full analysis with all bells and whistles
- **document_qa**: Just parse PDF and answer the question
- **research**: Web search only
- **calculation**: Finance calculations only
- **question**: Direct Claude response

### 3. **No Hardcoded Sections**
Claude generates its own structure based on the user's request. The prompt guides it on what to consider, but doesn't force a specific format.

### 4. **Streaming Responses**
Results stream to the frontend as they're generated, providing real-time feedback.

---

## Summary

**The orchestrator works like this:**

1. **User asks a question** → Frontend sends to backend
2. **Backend initializes state** → Creates initial state with message + PDF
3. **Router classifies intent** → Decides which tools to run
4. **Tools execute conditionally** → Only selected tools run
5. **Claude generates response** → Uses all gathered data
6. **Response streams back** → Frontend updates in real-time

**Key files to understand:**
- `backend/app.py` - Entry point, handles HTTP requests
- `backend/orchestrator/router.py` - Intent classification (traffic controller)
- `backend/orchestrator/graph.py` - LangGraph workflow (the brain)
- `backend/orchestrator/state.py` - State definition
- `backend/prompts/pre_screening.py` - Claude prompts

This architecture makes the system:
- ✅ **Flexible**: Responds naturally to any question
- ✅ **Efficient**: Only runs necessary tools
- ✅ **Scalable**: Easy to add new tools or intents
- ✅ **Maintainable**: Clear separation of concerns
