from langgraph.graph import StateGraph, END
from orchestrator.state import OrchestratorState
from orchestrator.router import classify_intent
from mcp import doc_parser, rag, web, finance, report
from bedrock_client import invoke_claude, invoke_claude_streaming
from prompts.pre_screening import PRE_SCREENING_PROMPT, SYSTEM_INSTRUCTIONS
from prompts.system import QA_SYSTEM_PROMPT, CALCULATION_SYSTEM_PROMPT
from typing import Dict, Any
import time

async def extract_pdf(state: OrchestratorState) -> OrchestratorState:
    """Extract text from PDF using Textract"""

    # Always try to extract if we have a file_url
    if not state.get("file_url"):
        return state

    start_time = time.time()
    state["tool_calls"].append({"tool": "doc_parser", "status": "started"})

    try:
        result = await doc_parser.extract_pdf_text(state["file_url"])
        state["pdf_text"] = result["text"]
        state["pdf_tables"] = result["tables"]

        duration_ms = int((time.time() - start_time) * 1000)
        state["tool_calls"].append({
            "tool": "doc_parser",
            "status": "completed",
            "duration_ms": duration_ms,
            "summary": f"Extracted {len(result['text'])} chars, {len(result['tables'])} tables"
        })
    except Exception as e:
        state["tool_calls"].append({
            "tool": "doc_parser",
            "status": "failed",
            "summary": str(e)
        })

    return state

async def search_rag(state: OrchestratorState) -> OrchestratorState:
    """Search vector DB for comparable deals"""

    if "rag" not in state.get("selected_tools", []):
        return state

    start_time = time.time()
    state["tool_calls"].append({"tool": "rag", "status": "started"})

    try:
        # Build query from user message or PDF content
        query = state["user_message"]
        if state.get("pdf_text"):
            query = state["pdf_text"][:500]  # First 500 chars

        results = await rag.search_similar(query, top_k=5)
        state["rag_results"] = results

        duration_ms = int((time.time() - start_time) * 1000)
        state["tool_calls"].append({
            "tool": "rag",
            "status": "completed",
            "duration_ms": duration_ms,
            "summary": f"Found {len(results)} comparable deals"
        })
    except Exception as e:
        state["tool_calls"].append({
            "tool": "rag",
            "status": "failed",
            "summary": str(e)
        })
        state["rag_results"] = []

    return state

async def search_web(state: OrchestratorState) -> OrchestratorState:
    """Search web for sponsor/market info - ALWAYS searches for latest/current info"""

    print(f"DEBUG: search_web() called with message: {state['user_message'][:100]}")
    print(f"DEBUG: selected_tools from state: {state.get('selected_tools', [])}")

    # Only search if "web" is in selected_tools (set by classify_intent)
    if "web" not in state.get("selected_tools", []):
        print(f"DEBUG: Skipping web search - 'web' not in selected_tools")
        return state

    start_time = time.time()
    state["tool_calls"].append({"tool": "web", "status": "started"})
    print(f"DEBUG: Running web search for query: {state['user_message'][:100]}")

    try:
        # Extract search queries using Claude
        # For now, use a simple query from the user message
        queries = [state["user_message"][:100]]

        results = await web.search_web_sources(queries=queries)
        state["web_results"] = results

        print(f"DEBUG: Web search found {len(results)} results")
        for i, result in enumerate(results[:3]):
            print(f"  Result {i+1}: {result.get('title', 'No title')[:50]} - {result.get('url', '')[:50]}")

        duration_ms = int((time.time() - start_time) * 1000)
        state["tool_calls"].append({
            "tool": "web",
            "status": "completed",
            "duration_ms": duration_ms,
            "summary": f"Found {len(results)} sources"
        })
    except Exception as e:
        state["tool_calls"].append({
            "tool": "web",
            "status": "failed",
            "summary": str(e)
        })
        state["web_results"] = []

    return state

async def calculate_finance(state: OrchestratorState) -> OrchestratorState:
    """Perform financial calculations - uses Claude to decide if calculations are needed"""

    from bedrock_client import invoke_claude

    # Use Claude to decide if financial calculations are needed
    decision_prompt = f"""Given this user question, determine if financial calculations are needed.

User question: {state['user_message']}

Financial calculations are needed if:
- The question explicitly asks to calculate metrics like DSCR, LTV, Cap Rate, IRR, NOI
- The question provides specific numbers and asks for financial analysis
- The question asks "what is the DSCR if..." or similar

Financial calculations are NOT needed if:
- The question just asks for definitions (e.g., "What is DSCR?")
- The question doesn't provide specific numbers to calculate
- The question is general knowledge about finance

Respond with ONLY "YES" or "NO".
"""

    try:
        decision = await invoke_claude(decision_prompt, "You are a helpful assistant that decides if financial calculations are needed.")
        decision = decision.strip().upper()
        print(f"DEBUG: Finance calculation decision for '{state['user_message'][:50]}...': {decision}")

        if "NO" in decision:
            return state

    except Exception as e:
        print(f"DEBUG: Error in finance decision: {e}, defaulting to skip")
        return state

    start_time = time.time()
    state["tool_calls"].append({"tool": "finance", "status": "started"})
    print(f"DEBUG: Running finance calculations for query: {state['user_message'][:100]}")

    try:
        # Extract numbers from PDF or user message using Claude
        # For now, use placeholder values
        metrics = await finance.calculate_metrics(
            noi=2_500_000,
            debt_service=1_800_000
        )

        state["finance_calcs"] = metrics

        duration_ms = int((time.time() - start_time) * 1000)
        state["tool_calls"].append({
            "tool": "finance",
            "status": "completed",
            "duration_ms": duration_ms,
            "summary": f"Calculated {len(metrics)} metrics"
        })
    except Exception as e:
        state["tool_calls"].append({
            "tool": "finance",
            "status": "failed",
            "summary": str(e)
        })
        state["finance_calcs"] = {}

    return state

async def generate_response(state: OrchestratorState) -> OrchestratorState:
    """Generate final response using Claude"""

    intent = state.get("intent", "question")

    if intent == "pre_screen":
        # Generate 10 sections using pre-screening prompt
        prompt = build_pre_screening_prompt(state)
        sections = []

        # For now, generate simple sections
        # In production, this would stream sections one by one
        async for text in invoke_claude_streaming(prompt, SYSTEM_INSTRUCTIONS):
            # Parse sections from streaming response
            # This is a simplified version
            pass

        # Placeholder sections
        section_titles = [
            "Executive Summary",
            "Sponsor Analysis",
            "Market & Submarket Analysis",
            "Competitive Set & Positioning",
            "Business Plan Viability",
            "Financial Underwriting",
            "Debt Structure & Financing Risk",
            "Legal, Regulatory & ESG",
            "Risk Factors & Red Flags",
            "Investment Fit & Strategy Alignment",
            "Scoring & Recommendation"
        ]

        for i, title in enumerate(section_titles):
            sections.append({
                "number": i,
                "title": title,
                "content": f"Analysis for {title} based on the provided data..."
            })

        state["sections"] = sections

    else:
        # Generate Q&A answer
        prompt = build_qa_prompt(state)
        state["answer"] = await invoke_claude(prompt, QA_SYSTEM_PROMPT)

    return state

async def create_docx(state: OrchestratorState) -> OrchestratorState:
    """Generate Word document for pre-screening"""

    if state.get("intent") != "pre_screen":
        return state

    if not state.get("sections"):
        return state

    start_time = time.time()
    state["tool_calls"].append({"tool": "report", "status": "started"})

    try:
        docx_url = await report.generate_docx(
            sections=state["sections"],
            title="Pre-Screening Analysis"
        )

        state["docx_url"] = docx_url

        duration_ms = int((time.time() - start_time) * 1000)
        state["tool_calls"].append({
            "tool": "report",
            "status": "completed",
            "duration_ms": duration_ms,
            "summary": "Word document created"
        })
    except Exception as e:
        state["tool_calls"].append({
            "tool": "report",
            "status": "failed",
            "summary": str(e)
        })

    return state

def build_pre_screening_prompt(state: OrchestratorState) -> str:
    """Build the full pre-screening prompt"""

    prompt = PRE_SCREENING_PROMPT + "\n\n"
    prompt += f"USER REQUEST:\n{state['user_message']}\n\n"

    if state.get("pdf_text"):
        prompt += f"PDF CONTENT:\n{state['pdf_text'][:5000]}\n\n"

    if state.get("rag_results"):
        prompt += "COMPARABLE DEALS:\n"
        for result in state["rag_results"][:3]:
            prompt += f"- {result}\n"
        prompt += "\n"

    if state.get("web_results"):
        prompt += "WEB RESEARCH:\n"
        for result in state["web_results"][:3]:
            prompt += f"- {result.get('title')}: {result.get('content', '')[:200]}\n"
        prompt += "\n"

    if state.get("finance_calcs"):
        prompt += "FINANCIAL CALCULATIONS:\n"
        for metric, data in state["finance_calcs"].items():
            prompt += f"- {metric}: {data.get('trail', '')}\n"
        prompt += "\n"

    return prompt

def build_qa_prompt(state: OrchestratorState) -> str:
    """Build Q&A prompt"""

    prompt = f"USER QUESTION: {state['user_message']}\n\n"

    # Web search results first (most important for current info)
    if state.get("web_results"):
        prompt += "=== WEB SEARCH RESULTS (USE THIS INFORMATION) ===\n"
        for i, result in enumerate(state["web_results"][:5], 1):
            prompt += f"\n{i}. {result.get('title', 'No title')}\n"
            if result.get('url'):
                prompt += f"   Source URL: {result.get('url')}\n"
            prompt += f"   Content: {result.get('content', '')}\n"
        prompt += "\n=== END WEB SEARCH RESULTS ===\n\n"

    if state.get("rag_results"):
        prompt += "Context from database:\n"
        for result in state["rag_results"][:3]:
            prompt += f"- {result}\n"
        prompt += "\n"

    if state.get("finance_calcs"):
        prompt += "Calculations:\n"
        for metric, data in state["finance_calcs"].items():
            prompt += f"- {metric}: {data.get('trail', '')}\n"
        prompt += "\n"

    prompt += "INSTRUCTIONS:\n"
    prompt += "1. Use the web search results above to answer the question\n"
    prompt += "2. Cite sources with URLs\n"
    prompt += "3. Be direct and concise\n"
    prompt += "4. If web results are provided, DO NOT say you lack information\n"

    return prompt

# Build the graph
def create_graph():
    workflow = StateGraph(OrchestratorState)

    # Add nodes
    workflow.add_node("classify", classify_intent)
    workflow.add_node("extract_pdf", extract_pdf)
    workflow.add_node("search_rag", search_rag)
    workflow.add_node("search_web", search_web)
    workflow.add_node("calculate", calculate_finance)
    workflow.add_node("generate", generate_response)
    workflow.add_node("create_docx", create_docx)

    # Define flow
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "extract_pdf")
    workflow.add_edge("extract_pdf", "search_rag")
    workflow.add_edge("search_rag", "search_web")
    workflow.add_edge("search_web", "calculate")
    workflow.add_edge("calculate", "generate")
    workflow.add_edge("generate", "create_docx")
    workflow.add_edge("create_docx", END)

    return workflow.compile()
