from typing import TypedDict, List, Optional, Annotated, Dict, Any
import operator

class OrchestratorState(TypedDict):
    # Input
    conversation_id: str
    user_message: str
    file_url: Optional[str]

    # Routing
    intent: str  # "pre_screen", "question", "calculation", "research"
    requires_pdf: bool
    selected_tools: List[str]

    # Tool outputs
    pdf_text: Optional[str]
    pdf_tables: List[Dict[str, Any]]
    rag_results: List[Dict[str, Any]]
    web_results: List[Dict[str, Any]]
    finance_calcs: Dict[str, Any]

    # Final output
    sections: Optional[List[Dict[str, Any]]]  # For pre-screening
    answer: Optional[str]                      # For Q&A
    docx_url: Optional[str]

    # Metadata
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]
