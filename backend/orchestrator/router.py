from orchestrator.state import OrchestratorState
from bedrock_client import invoke_claude, parse_json

async def classify_intent(state: OrchestratorState) -> OrchestratorState:
    """Use Claude to classify user intent and decide which tools to use"""

    print(f"DEBUG: Full user prompt: {state['user_message']}")
    print(f"DEBUG: User prompt length: {len(state['user_message'])} characters")
    print(f"DEBUG: classify_intent() called with message: {state['user_message'][:100]}")

    # Simple keyword-based classification for now (instead of calling Claude)
    # This is more reliable and faster
    message_lower = state['user_message'].lower()

    # Default intent
    intent = "question"
    requires_pdf = False
    selected_tools = []

    # Check if user wants a Word document output
    wants_document = any(keyword in message_lower for keyword in [
        'word document', 'downloadable', 'download', 'document', '.docx', 'formatted as',
        'report', 'analysis', 'memo', 'generate', 'create a'
    ])

    # Check for EXPLICIT pre-screening request (must mention these specific keywords)
    if state.get('file_url') and any(keyword in message_lower for keyword in [
        'pre-screen', 'pre screen', 'prescreening', 'full analysis',
        'complete analysis', 'investment analysis', 'underwriting analysis',
        'analyze this om', 'analyze this offering memorandum', 'review the attached',
        'analyze', 'analysis'
    ]):
        intent = "pre_screen"
        requires_pdf = True
        # Include report tool if document output is requested or it's an analysis
        selected_tools = ["doc_parser", "rag", "web", "finance"]
        if wants_document:
            selected_tools.append("report")

    # PDF attached but asking a specific question -> treat as document Q&A
    elif state.get('file_url'):
        intent = "document_qa"
        requires_pdf = True
        selected_tools = ["doc_parser"]  # Just parse the PDF and answer the question

    # Check for current/latest information requests (trigger web search)
    elif any(keyword in message_lower for keyword in ['latest', 'current', 'recent', 'today', 'now', '2025', '2024', '2023']):
        intent = "research"
        selected_tools = ["web"]

    # Check for calculation requests
    elif any(keyword in message_lower for keyword in ['calculate', 'dscr', 'ltv', 'cap rate', 'irr', 'noi', 'debt service']):
        intent = "calculation"
        selected_tools = ["finance"]

    # Default: just a question
    else:
        intent = "question"
        selected_tools = []

    print(f"DEBUG: Classified intent={intent}, requires_pdf={requires_pdf}, selected_tools={selected_tools}")

    state["intent"] = intent
    state["requires_pdf"] = requires_pdf
    state["selected_tools"] = selected_tools

    return state
