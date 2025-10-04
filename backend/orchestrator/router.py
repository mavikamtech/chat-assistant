from orchestrator.state import OrchestratorState
from bedrock_client import invoke_claude, parse_json

async def classify_intent(state: OrchestratorState) -> OrchestratorState:
    """Use Claude to classify user intent and decide which tools to use"""

    print(f"DEBUG: classify_intent() called with message: {state['user_message'][:100]}")

    # Simple keyword-based classification for now (instead of calling Claude)
    # This is more reliable and faster
    message_lower = state['user_message'].lower()

    # Default intent
    intent = "question"
    requires_pdf = False
    selected_tools = []

    # Check for pre-screening (if PDF is attached)
    if state.get('file_url'):
        intent = "pre_screen"
        requires_pdf = True
        selected_tools = ["doc_parser", "rag", "web", "finance", "report"]

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
