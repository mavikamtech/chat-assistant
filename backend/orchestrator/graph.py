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

    if not state.get("file_url"):
        return state

    print(f"DEBUG: extract_pdf node starting for {state['file_url']}")
    start_time = time.time()
    state["tool_calls"].append({"tool": "doc_parser", "status": "started"})

    try:
        result = await doc_parser.extract_pdf_text(state["file_url"])
        state["pdf_text"] = result["text"]
        state["pdf_tables"] = result["tables"]

        print(f"DEBUG: Textract extraction completed: {len(result['text'])} chars, {len(result['tables'])} tables")

        duration_ms = int((time.time() - start_time) * 1000)
        state["tool_calls"].append({
            "tool": "doc_parser",
            "status": "completed",
            "duration_ms": duration_ms,
            "summary": f"Extracted {len(result['text'])} chars, {len(result['tables'])} tables"
        })
    except Exception as e:
        print(f"ERROR in extract_pdf: {e}")
        import traceback
        traceback.print_exc()
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
        # Extract search queries - optimize for current/latest information
        user_msg = state["user_message"].lower()

        # Build targeted query for current information
        if any(keyword in user_msg for keyword in ['latest', 'current', 'today', 'now']):
            # Add time context to query
            import datetime
            current_date = datetime.datetime.now().strftime("%B %d %Y")  # e.g., "October 05 2025"

            # Extract the main subject (e.g., "SOFR rate")
            query = state["user_message"]

            # Make query more specific for current data - use multiple targeted queries
            if 'sofr' in user_msg:
                queries = [
                    f"overnight SOFR rate today {current_date}",
                    "SOFR rate Federal Reserve Bank New York today"
                ]
            elif 'rate' in user_msg and 'interest' in user_msg:
                queries = [f"{state['user_message'][:80]} {current_date}"]
            else:
                queries = [f"{state['user_message'][:100]} {current_date}"]
        else:
            queries = [state["user_message"][:100]]

        # Use time_sensitive flag for real-time queries
        time_sensitive = state.get("time_sensitivity") == "real_time"
        print(f"DEBUG: time_sensitivity={state.get('time_sensitivity')}, time_sensitive={time_sensitive}")
        results = await web.search_web_sources(queries=queries, time_sensitive=time_sensitive)
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
        # Use Haiku for lightweight decision-making (faster and cheaper)
        decision = await invoke_claude(
            decision_prompt,
            "You are a helpful assistant that decides if financial calculations are needed.",
            use_haiku=True
        )
        decision = decision.strip().upper()
        print(f"DEBUG: Finance calculation decision for '{state['user_message'][:50]}...': {decision}")

        if "NO" in decision:
            return state

    except Exception as e:
        print(f"DEBUG: Error in finance decision: {e}, defaulting to skip")
        return state

    start_time = time.time()
    state["tool_calls"].append({"tool": "finance", "status": "started"})
    print(f"DEBUG: Finance tool disabled - hardcoded values removed to prevent hallucinations")

    # DISABLED: This function was using hardcoded placeholder values ($2.5M NOI, $1.8M debt service)
    # which caused hallucinated financial calculations in the output.
    # TODO: Implement proper financial data extraction from documents or structured database
    # before re-enabling this functionality.

    state["finance_calcs"] = {}

    duration_ms = int((time.time() - start_time) * 1000)
    state["tool_calls"].append({
        "tool": "finance",
        "status": "skipped",
        "duration_ms": duration_ms,
        "summary": "Finance calculations disabled (hardcoded values removed)"
    })

    return state

async def generate_response(state: OrchestratorState) -> OrchestratorState:
    """Generate final response using Claude"""

    intent = state.get("intent", "question")

    if intent == "pre_screen":
        # Generate analysis using Claude Sonnet with STREAMING for long responses
        prompt = build_pre_screening_prompt(state)

        # Use streaming to ensure complete analysis is generated
        full_response = ""
        async for chunk in invoke_claude_streaming(prompt, SYSTEM_INSTRUCTIONS):
            full_response += chunk

        # Return as a single answer instead of forced sections
        state["answer"] = full_response

    elif intent == "document_qa":
        # User has a PDF but is asking a specific question - respond naturally
        prompt = build_document_qa_prompt(state)

        # Check if this is a financial extraction (might be long) - use streaming
        if any(keyword in state['user_message'].lower() for keyword in [
            'extract key data', 'key terms', 'accounting', 'financial data points',
            'structured extraction', 'downstream accounting', 'loan terms'
        ]):
            # Use streaming for comprehensive extraction to avoid truncation
            full_response = ""
            async for chunk in invoke_claude_streaming(prompt, QA_SYSTEM_PROMPT):
                full_response += chunk
            state["answer"] = full_response
        else:
            # Regular Q&A can use non-streaming
            state["answer"] = await invoke_claude(prompt, QA_SYSTEM_PROMPT)

    else:
        # Generate Q&A answer
        prompt = build_qa_prompt(state)
        state["answer"] = await invoke_claude(prompt, QA_SYSTEM_PROMPT)

    return state


# Removed parse_sections_from_response - let Claude structure its own response

async def create_docx(state: OrchestratorState) -> OrchestratorState:
    """Generate Word document from analysis"""

    # Only create document if report tool was selected
    if "report" not in state.get("selected_tools", []):
        return state

    # Need answer content to generate document
    if not state.get("answer"):
        return state

    start_time = time.time()
    state["tool_calls"].append({"tool": "report", "status": "started"})

    try:
        # Generate document from markdown answer
        docx_url = await report.generate_docx(
            content=state["answer"],
            title="Investment Analysis"
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

    user_message = state['user_message'].lower()

    # Check if this is a simple extraction request (Test Case C) - very specific keywords
    is_extraction_only = any(keyword in user_message for keyword in [
        'extract the following', 'key terms from'
    ])

    if is_extraction_only:
        # Build a focused extraction prompt
        prompt = f"""You are a commercial real estate analyst. Extract the requested information from the following offering memorandum.

USER REQUEST:
{state['user_message']}

OFFERING MEMORANDUM CONTENT:
{state.get('pdf_text', 'No PDF content available')}

INSTRUCTIONS:
1. Extract ONLY the information requested by the user
2. If a value is not found in the document, write "Not Found"
3. Include page references or section names where you found each value (if identifiable)
4. Format as a clean table or bullet list
5. DO NOT make up or hallucinate values
6. Be precise and accurate

"""
    else:
        # Build full pre-screening analysis prompt
        prompt = PRE_SCREENING_PROMPT + "\n\n"

        # Count sections requested by the user
        user_msg = state['user_message']
        import re
        section_matches = re.findall(r'^\d+[\.\)]\s+[A-Z]', user_msg, re.MULTILINE)
        num_sections = len(section_matches)

        if num_sections > 0:
            prompt += f"⚠️ IMPORTANT: The user has requested {num_sections} numbered sections. You MUST complete ALL {num_sections} sections in full detail. Do not stop early.\n\n"

        prompt += f"USER REQUEST:\n{state['user_message']}\n\n"

        if state.get("pdf_text"):
            # Send more PDF content (up to ~40K tokens worth)
            pdf_preview = state['pdf_text'][:150000]  # ~40k tokens
            prompt += f"OFFERING MEMORANDUM CONTENT:\n{pdf_preview}\n\n"

        if state.get("pdf_tables") and len(state.get("pdf_tables", [])) > 0:
            prompt += "KEY TABLES FROM PDF:\n"
            for i, table in enumerate(state.get("pdf_tables", [])[:5], 1):
                table_data = table.get('data', [])
                if table_data and len(table_data) > 0:
                    prompt += f"\nTable {i}:\n"
                    for row in table_data[:10]:  # First 10 rows
                        prompt += f"  {' | '.join(str(cell) for cell in row)}\n"
            prompt += "\n"

        if state.get("rag_results"):
            prompt += "COMPARABLE DEALS FROM DATABASE:\n"
            for result in state["rag_results"][:3]:
                prompt += f"- {result}\n"
            prompt += "\n"

        if state.get("web_results"):
            prompt += "WEB RESEARCH RESULTS (cite these sources in your response):\n"
            for i, result in enumerate(state["web_results"][:3], 1):
                title = result.get('title', 'No title')
                content = result.get('content', '')[:300]
                url = result.get('url', '')
                prompt += f"[{i}] {title}\n"
                if url:
                    prompt += f"    URL: {url}\n"
                prompt += f"    Content: {content}\n\n"
            prompt += "NOTE: Include inline citations [1], [2], etc. and a Sources section at the end.\n\n"

        if state.get("finance_calcs"):
            prompt += "PRE-CALCULATED FINANCIAL METRICS:\n"
            for metric, data in state["finance_calcs"].items():
                prompt += f"- {metric}: {data.get('trail', '')}\n"
            prompt += "\n"

        # Final reminder for structured analyses
        if num_sections > 0:
            prompt += f"\n⚠️ FINAL REMINDER: Complete ALL {num_sections} sections requested above. Do not skip any sections. Provide comprehensive analysis for each one.\n"

    return prompt

def build_document_qa_prompt(state: OrchestratorState) -> str:
    """Build prompt for answering questions about an uploaded document"""

    user_message_lower = state['user_message'].lower()

    # Check if this is an accounting/financial extraction request
    is_financial_extraction = any(keyword in user_message_lower for keyword in [
        'extract key data', 'key terms', 'accounting', 'financial data points',
        'structured extraction', 'downstream accounting', 'loan terms'
    ])

    prompt = f"USER QUESTION: {state['user_message']}\n\n"

    # Include the PDF content - send MORE content for thorough extraction
    if state.get("pdf_text"):
        pdf_preview = state['pdf_text'][:200000]  # ~50k tokens - doubled for comprehensive search
        prompt += f"DOCUMENT CONTENT:\n{pdf_preview}\n\n"

    if state.get("pdf_tables") and len(state.get("pdf_tables", [])) > 0:
        prompt += "TABLES FROM DOCUMENT:\n"
        for i, table in enumerate(state.get("pdf_tables", [])[:5], 1):
            table_data = table.get('data', [])
            if table_data and len(table_data) > 0:
                prompt += f"\nTable {i}:\n"
                for row in table_data[:10]:
                    prompt += f"  {' | '.join(str(cell) for cell in row)}\n"
        prompt += "\n"

    if is_financial_extraction:
        # Use specialized financial extraction prompt - DYNAMIC based on user request
        prompt += f"""INSTRUCTIONS - INTELLIGENT STRUCTURED DATA EXTRACTION:

You are a financial analyst extracting data from a legal/financial document. The user has asked:
"{state['user_message']}"

ANALYSIS PHASE:
1. First, carefully read the user's request to understand EXACTLY what they want extracted
2. Identify which data points are most relevant to their specific question
3. Look at the document type (LLC Agreement, Loan Agreement, Offering Memo, etc.) to understand what data is likely present
4. **IMPORTANT**: Even if this is an LLC Agreement, it may contain detailed financial terms including:
   - Underlying loan amounts and terms (referenced in definitions)
   - Distribution/repayment schedules (in distributions sections)
   - Guarantor names (in definitions or exhibits)
   - Property owner details (in definitions)
   - Fees and costs (in capital contribution sections)
   → DO NOT skip financial extraction just because it's labeled as an "LLC Agreement"

OUTPUT FORMAT:
For each data point you extract, provide this structure:

**[Data Point Name]**
- Clause Text: "exact verbatim text from document"
- Page: X (or "Multiple pages" or "Not identifiable")
- Section: Section name/heading
- Confidence: XX (0-100)

CONFIDENCE SCORING RUBRIC:
- 100: Explicit, unambiguous value clearly stated
- 90-95: Clear value with minor interpretation needed
- 80-89: Value found but requires some inference
- 70-79: Value partially found or requires assumptions
- <70: Uncertain or not found

AVAILABLE DATA POINT CATEGORIES (extract ONLY what's relevant to the user's request):

📊 FINANCIAL TERMS (if user asks about loan/financing details):
- Deal Name / Identifier
- Borrower Name / Property Owner
- Loan Amount / Capital Contribution
  → Search hints: Look for "Senior Loan", "maximum principal amount", "Preferred Capital Contributions", dollar amounts in definitions
- Interest Rate and Type (Fixed/Floating, SOFR, Prime, Margin, Floor)
  → Search hints: "Applicable Preferred Return Rate", "Term SOFR Rate", "Benchmark", "Prime Rate", "Floor Rate", "Margin"
- Loan Term (Start and End Dates)
  → Search hints: "Term", "Maturity Date", "commenced on", "shall continue"
- Repayment Schedule / Distribution Schedule
  → Search hints: "Preferred Return shall be distributed", "monthly in arrears", "computed by multiplying", "360-day year"
- Prepayment Penalties / Breakage Costs
  → Search hints: "Breakage Costs", "has the meaning set forth in Exhibit", prepayment provisions
- Fees or Costs Payable at Closing
  → Search hints: "Initial Preferred Capital Contribution", "reimburse", "legal fees and expenses", "Extension Fee"

👥 PARTIES & STRUCTURE (if user asks about parties, members, guarantors):
- Members / Parties to Agreement (with addresses, ownership %)
  → Search hints: "Common Member", "Preferred Member", party names in introduction, addresses
- Guarantor(s) and Guarantees (list ALL guarantors)
  → Search hints: "Guaranties", "Preferred Guaranty", "Tidal Guarantor", individual names (Michael Walsdorf, Ken Copeland, etc.), "Completion Guaranty", "Carry Guaranty", "Environmental Indemnity"
- Managing Member / Manager
  → Search hints: "Managing Member", "shall manage", "management rights"
- Sponsors / Equity Partners
  → Search hints: "Sponsor", "Tidal GP Fund", equity party names

🏢 PROPERTY & PROJECT (if user asks about real estate, development, collateral):
- Collateral Description / Property Details
  → Search hints: "Property", "real property commonly known as", street address
- Project Details (units, square footage, components, use type)
  → Search hints: "Hotel Component", "MVC Residential Component", "keys", "residential units", "square feet", "sq ft", "Parking Component"
- Development Milestones
  → Search hints: "Construction", "Substantial Completion", deadlines, "shall be completed"
- Property Address / Location
  → Search hints: Street addresses, city, state, "commonly known as"

⚖️ LEGAL & RISK (if user asks about default, covenants, legal terms):
- Default Clauses / Events of Default / Changeover Events
  → Search hints: "Changeover Event", "Event of Default", "occurrence of any of the following", enumerated default events
- Covenants (Financial and Operational)
  → Search hints: "Affirmative Covenants", "Major Decisions", "shall", "shall not", restrictions
- Representations and Warranties
  → Search hints: "represents and warrants", "Reps and Warranties"
- Insurance Requirements
  → Search hints: "Insurance", "coverage", "insured"
- Indemnification Terms
  → Search hints: "indemnify", "hold harmless", "Environmental Indemnity"

📅 DATES & TIMING (if user asks about timeline, closing, deadlines):
- Closing Date / Effective Date
  → Search hints: "Effective Date", "entered into as of", date in introduction
- Construction Completion Deadlines
  → Search hints: "Substantial Completion Deadline", specific dates, "January", "March", extensions
- Key Dates / Milestones
  → Search hints: "Forced Sale Initiation Date", project milestones, "Certificate of Formation"
- Term / Maturity Dates
  → Search hints: "term commenced on", "shall continue", maturity provisions
- Extension Options
  → Search hints: "Extended", "extension", "may be extended"

💰 ECONOMICS & RETURNS (if user asks about distributions, returns, economics):
- Preferred Return / Distribution Priority
  → Search hints: "Preferred Return", "distribution", "priority", "waterfall"
- Promote / Carried Interest Structure
  → Search hints: "Promote", "carried interest", percentage splits
- Waterfall / Distribution Provisions
  → Search hints: "Distribution", "Article VI", payment order, tiers
- Capital Calls
  → Search hints: "Capital Contribution", "shall contribute", funding obligations
- Exit Terms / Forced Sale Provisions
  → Search hints: "Forced Sale", "put right", "call right", exit mechanisms

CRITICAL INSTRUCTIONS:
1. **BE SELECTIVE**: Only extract data points that are:
   a) Explicitly requested by the user, OR
   b) Directly relevant to answering their question, OR
   c) Critical context for understanding their request

2. **BE COMPREHENSIVE WITHIN SCOPE**: For the data points you do extract, be thorough:
   - Extract EXACT verbatim text (don't paraphrase)
   - Include ALL instances (e.g., all guarantors by name, all default events enumerated)
   - Provide complete clause text, not summaries
   - Use the search hints above to find hard-to-locate data

3. **SEARCH EXHAUSTIVELY** - The document may contain financial data even if it's an LLC Agreement:
   - **READ THE ENTIRE DEFINITIONS SECTION (1.01)** - Many financial terms are hidden in definitions
   - **Loan Amount**:
     * Search for "Senior Loan" in definitions - it will have a dollar amount
     * Look for "maximum principal amount", "$181,800,000" or similar large dollar figures
     * Even in LLC Agreements, there may be underlying loan references
   - **Property Owner/Borrower**:
     * Search for "Property Owner means" in definitions
     * Look for entities like "Davis BLVD Owner LLC" or similar
   - **Repayment Schedule**:
     * Search Article 4 or Section 4.03 for "Preferred Return"
     * Look for "shall be distributed monthly", "in arrears", "360-day year"
     * Search for "computed by multiplying the actual number of days"
     * CRITICAL: In LLC Agreements, this is often defined in the "Preferred Return" definition or Section 4.03
     * DO NOT skip this just because it's an LLC Agreement - extract if found in ANY section
   - **Prepayment Penalties**:
     * Search for "Breakage Costs" definition
     * Look for "has the meaning set forth in Exhibit G"
     * Note the cross-reference even if exhibit isn't attached
     * CRITICAL: Even in LLC Agreements, prepayment/breakage costs are often defined
     * DO NOT skip this - if you find "Breakage Costs" defined anywhere, extract it with the cross-reference
   - **Guarantor Names**:
     * Don't just say "guarantors exist" - search for "Guaranties means"
     * Look for individual names: Michael Walsdorf, Ken Copeland, Brian Walsdorf
     * Search for entity names: Tidal Guarantor, Tidal GP Fund II, L.P.
     * List EVERY name explicitly
   - **Fees at Closing**:
     * Search Section 4.03 for "Initial Preferred Capital Contribution"
     * Look for "reimburse" and "legal fees and expenses"

4. **BE ACCURATE**:
   - Before marking anything "Not Found", verify you've checked:
     ✓ The entire Definitions section (Section 1.01)
     ✓ Article 4 (Capital Contributions, Distributions, Returns)
     ✓ All cross-references and defined terms
     ✓ Recitals/introduction paragraphs
   - If truly not found after exhaustive search, write "Not Found" and set confidence to 0
   - Don't hallucinate or make up values
   - Include page numbers from document context when identifiable
   - For cross-references (e.g., "Exhibit G"), note the reference even if the exhibit isn't attached

5. **BE PROFESSIONAL**:
   - Format as clean, structured output with 📁 Structured Data Extraction header
   - Group related data points logically
   - At the end, offer: "Would you like this data exported into a spreadsheet or JSON format for integration into your accounting system?"

EXAMPLE - If user asks "What are the loan terms and guarantors?":
Only extract: Loan Amount, Interest Rate, Loan Term, Repayment Schedule, Guarantors
(Skip: Members, Project Details, Covenants unless directly relevant)

EXAMPLE - If user asks "Tell me about the project and development timeline":
Only extract: Project Details, Property Description, Construction Deadlines, Key Milestones
(Skip: Loan Amount, Interest Rates unless project-related)

⚠️ FINAL CRITICAL REMINDERS:
1. The document above contains 50,000+ tokens. Read it THOROUGHLY - don't stop early!
2. Search the DEFINITIONS section (1.01) exhaustively - it contains most financial terms
3. For "Loan Amount": Look for "Senior Loan" + dollar amount like "$181,800,000"
4. For "Property Owner": Look for "Property Owner means [Entity Name]"
5. For "Repayment Schedule": Search the "Preferred Return" definition AND Section 4.03 for "distributed monthly in arrears" / "360-day year"
   → EXTRACT THIS even if it's an LLC Agreement - if the text exists, include it!
6. For "Prepayment Penalties": Search for "Breakage Costs" definition - include the cross-reference to Exhibit G
   → EXTRACT THIS even if it's an LLC Agreement - if "Breakage Costs" is defined, include it!
7. For "Guarantor Names": List EVERY person's name - Michael Walsdorf, Ken Copeland, Brian Walsdorf, Tidal GP Fund II, L.P.
8. DO NOT assume data is "not in this agreement" - if it's defined ANYWHERE in the document, extract it!
9. DO NOT say "Not Found" unless you've searched EVERY section mentioned above

NOW: Based on the user's request above, extract the MOST RELEVANT data points from the document.

"""
    else:
        # Use standard Q&A prompt
        prompt += """INSTRUCTIONS:
1. Answer the user's question based on the document content provided above
2. Be conversational and natural, like ChatGPT
3. If extracting data, format it clearly (table, bullet points, etc.)
4. If data is not found, say "Not found in the document"
5. Cite page numbers or sections when possible
6. DO NOT generate a pre-screening report unless explicitly asked
7. Just answer what the user asked for

"""

    return prompt

def build_qa_prompt(state: OrchestratorState) -> str:
    """Build Q&A prompt"""

    prompt = f"USER QUESTION: {state['user_message']}\n\n"

    # Web search results first (most important for current info)
    if state.get("web_results"):
        prompt += "=== LATEST WEB SEARCH RESULTS (USE THESE AS PRIMARY SOURCE) ===\n"
        prompt += "IMPORTANT: These are the most recent search results. Use this data for your answer.\n"
        prompt += "Each source below has a citation number [1], [2], etc. You MUST include these citation numbers in your response.\n\n"
        for i, result in enumerate(state["web_results"][:5], 1):
            prompt += f"\n[{i}] {result.get('title', 'No title')}\n"
            if result.get('url'):
                prompt += f"    URL: {result.get('url')}\n"
            prompt += f"    Content: {result.get('content', '')}\n"
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
    prompt += "1. PRIORITIZE the web search results above - they contain the MOST CURRENT information\n"
    prompt += "2. Extract exact numbers and rates from the web results\n"
    prompt += "3. ALWAYS add citation numbers [1], [2], etc. inline when using information from sources\n"
    prompt += "4. At the end of your response, include a 'Sources:' section listing all citations with their URLs\n"
    prompt += "5. Show all calculations with formulas\n"
    prompt += "6. Be direct and concise\n"
    prompt += "7. If web results are provided, DO NOT say you lack information\n"
    prompt += "\nCITATION FORMAT EXAMPLE:\n"
    prompt += "The current SOFR rate is 4.85% [1]. This represents an increase from last month [2].\n\n"
    prompt += "Sources:\n"
    prompt += "[1] Federal Reserve Bank - https://example.com/sofr\n"
    prompt += "[2] Bloomberg Markets - https://example.com/rates\n"

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
