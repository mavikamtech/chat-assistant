from orchestrator.state import OrchestratorState
from bedrock_client import invoke_claude, parse_json
from datetime import datetime

def safe_print(message: str):
    """Print message with safe Unicode handling for Windows console"""
    try:
        # Try to encode to the console's encoding first
        import sys
        if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
            safe_msg = message.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
            print(safe_msg)
        else:
            # Fallback to ASCII
            print(message.encode('ascii', 'replace').decode('ascii'))
    except Exception:
        # Final fallback - just remove non-ASCII
        print(''.join(char if ord(char) < 128 else '?' for char in message))

async def classify_intent(state: OrchestratorState) -> OrchestratorState:
    """Use Claude to classify user intent with temporal awareness and decide which tools to use"""

    safe_print(f"DEBUG: Full user prompt: {state['user_message']}")
    safe_print(f"DEBUG: User prompt length: {len(state['user_message'])} characters")
    safe_print(f"DEBUG: classify_intent() called with message: {state['user_message'][:100]}")

    user_message = state['user_message']
    has_file = bool(state.get('file_url'))
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Use Claude (Haiku for speed) to classify intent with temporal awareness
    classification_prompt = f"""Analyze this user query and classify the intent with temporal awareness.

Current date: {current_date}
User has attached a PDF: {has_file}
User query: "{user_message}"

Classify the intent and determine which tools are needed. Consider temporal context carefully:
- "past 10 days", "last week", "recent" = real-time data → use web search
- "2023 data", "historical", "archived" = old data → use database/RAG
- "calculate DSCR" = financial calculation → use finance tool
- PDF attached + analysis request = document analysis

Intent types:
1. pre_screen - Full property/deal analysis (requires PDF)
2. document_qa - Specific question about attached PDF
3. market_research - Real-time market data (past days/weeks/months)
4. historical_query - Historical data from database (specific past years)
5. calculation - Financial calculations (DSCR, LTV, IRR, etc.)
6. general_question - General knowledge question

Available tools:
- doc_parser: Parse PDF documents
- rag: Search historical database/knowledge base
- web: Real-time web search for current data
- finance: Financial calculations
- report: Generate Word document output

CRITICAL:
- Queries about "past 10 days", "last week", "recent trends" should use WEB tool (not RAG)
- Queries about "2023", "last year's data", "historical" should use RAG tool
- If user wants downloadable/Word document output, include report tool

Return JSON with this exact structure:
{{
  "intent": "intent_type",
  "selected_tools": ["tool1", "tool2"],
  "time_sensitivity": "real_time|historical|none",
  "requires_pdf": true/false,
  "wants_document_output": true/false,
  "reasoning": "brief explanation"
}}"""

    try:
        # Use Haiku for fast classification
        response = await invoke_claude(classification_prompt, use_haiku=True)
        safe_print(f"DEBUG: Claude classification response: {response}")

        # Parse the JSON response
        classification = parse_json(response)

        intent = classification.get("intent", "general_question")
        selected_tools = classification.get("selected_tools", [])
        time_sensitivity = classification.get("time_sensitivity", "none")
        requires_pdf = classification.get("requires_pdf", False)
        wants_document_output = classification.get("wants_document_output", False)

        safe_print(f"DEBUG: Classified intent={intent}, time_sensitivity={time_sensitivity}, requires_pdf={requires_pdf}, selected_tools={selected_tools}")

    except Exception as e:
        # Fallback to simple keyword-based classification if Claude fails
        print(f"ERROR: Classification failed: {e}. Falling back to keyword matching.")

        message_lower = user_message.lower()

        # Fallback logic with temporal awareness
        if has_file and any(kw in message_lower for kw in ['analyze', 'analysis', 'pre-screen', 'review']):
            intent = "pre_screen"
            selected_tools = ["doc_parser", "rag", "web", "finance"]
            requires_pdf = True
            wants_document_output = any(kw in message_lower for kw in ['document', 'report', 'download', '.docx'])
        elif has_file:
            intent = "document_qa"
            selected_tools = ["doc_parser"]
            requires_pdf = True
            wants_document_output = False
        # Temporal awareness in fallback
        elif any(kw in message_lower for kw in ['past', 'last', 'days', 'weeks', 'recent', 'current', 'latest', 'now']):
            intent = "market_research"
            selected_tools = ["web"]
            requires_pdf = False
            wants_document_output = False
        elif any(kw in message_lower for kw in ['calculate', 'dscr', 'ltv', 'cap rate', 'irr']):
            intent = "calculation"
            selected_tools = ["finance"]
            requires_pdf = False
            wants_document_output = False
        else:
            intent = "general_question"
            selected_tools = []
            requires_pdf = False
            wants_document_output = False

        time_sensitivity = "none"

    state["intent"] = intent
    state["requires_pdf"] = requires_pdf
    state["selected_tools"] = selected_tools
    state["time_sensitivity"] = time_sensitivity
    state["wants_document_output"] = wants_document_output

    return state
