✅ Smoke Test & UAT Plan for CRE Private Credit Sub-Agent
🧪 1. Test Objectives
    • Validate that the LLM-based sub-agent can: 
        ○ Accurately parse and analyze Offering Memorandums (PDFs) and Excel models.
        ○ Perform real-time financial calculations using external data (e.g., SOFR).
        ○ Extract and summarize key terms from documents.
    • Ensure outputs are structured, evidence-based, and analyst-grade.
    • Confirm integration with your internal system (e.g., OneDrive, Bedrock, Lambda, etc.) works as expected.

🔍 2. Test Scenarios
A. Offering Memorandum Pre-Screening
Goal: Validate that the system can ingest an OM + Excel model and generate a structured pre-screening memo.
Test Inputs:
    • Upload a real OM (PDF) and Excel model from a past deal.
    • Prompt:
"Pre-screen this multifamily deal. Extract key metrics (DSCR, LTV, NOI, CapEx), summarize the business plan, and flag any underwriting red flags. Format output as a Word memo."
Expected Output:
    • Structured memo with: 
        ○ Deal summary
        ○ Key financial metrics (with source references)
        ○ Business plan summary
        ○ Risk flags
        ○ Analyst-style commentary
Validation Criteria:
    • ✅ Accuracy of extracted metrics (cross-check with Excel)
    • ✅ Correct identification of red flags (e.g., aggressive rent growth)
    • ✅ Memo formatting and clarity
    • ✅ Time to completion (target < 2 min)

B. Real-Time Financial Analysis
Goal: Validate dynamic data retrieval and calculation logic.
Prompt:
"What is the latest overnight SOFR rate? Based on that, calculate the interest cost on a $25M loan with a 2.5% spread. Show the formula and result."
Expected Output:
    • Latest SOFR rate (with source citation)
    • Formula:
Interest = Principal × (SOFR + Spread)
    • Result: e.g.,
$25,000,000 × (5.33% + 2.5%) = $1,958,000 annual interest
Validation Criteria:
    • ✅ Correct SOFR rate (check against NY Fed)
    • ✅ Accurate formula and math
    • ✅ Clear explanation

C. Key Term Extraction & Summarization
Goal: Validate that the system can extract and summarize key terms from documents.
Prompt:
"Extract the following from this OM: sponsor name, asset type, location, loan amount, interest rate, term, DSCR, LTV, exit strategy, and business plan summary."
Expected Output:
    • Structured table or bullet list with: 
        ○ Each term filled in (or marked “Not Found” if missing)
        ○ Source page or section reference (if possible)
Validation Criteria:
    • ✅ Completeness of extraction
    • ✅ Accuracy of values
    • ✅ Reference to source location (if implemented)

🧪 3. Smoke Test Checklist
Test Area	Test	Pass/Fail	Notes
File Ingestion	Can system ingest PDF + Excel?	✅ / ❌	
Prompt Parsing	Does it understand the prompt intent?	✅ / ❌	
Metric Extraction	Are DSCR, LTV, NOI, etc. accurate?	✅ / ❌	
Memo Generation	Is the output structured and readable?	✅ / ❌	
External Data	Can it fetch SOFR reliably?	✅ / ❌	
Math Accuracy	Are interest calculations correct?	✅ / ❌	
Summarization	Are key terms extracted correctly?	✅ / ❌	
Error Handling	Does it gracefully handle missing data?	✅ / ❌	
Performance	Does it respond within 2 minutes?	✅ / ❌	

🧠 4. Suggestions to Improve Prompt Design
    • Be explicit about format:
“Return a Word-formatted memo with sections: Executive Summary, Key Metrics Table, Risk Commentary.”
    • Use role-based framing:
“Act as a senior CRE credit analyst. Your task is to…”
    • Add fallback behavior:
“If a value is not found, state ‘Not Found’ and do not hallucinate.”
    • Encourage source referencing:
“For each extracted value, include the page number or section from the OM.”

🧪 5. UAT Execution Tips
    • Run tests with 3–5 real deals across asset types (multifamily, retail, industrial).
    • Include edge cases: missing data, poor formatting, aggressive assumptions.
    • Have a senior analyst review outputs for quality scoring.
    • Log all outputs and errors for debugging and fine-tuning.


----------------------------------


✅ UAT Success Criteria for CRE Sub-Agent
🎯 1. Functional Accuracy
Criteria	Description	Pass/Fail	Notes
Key Metric Extraction	DSCR, LTV, NOI, CapEx, loan terms, etc. are correctly extracted from OM and Excel	✅ / ❌	Cross-check with source
Business Plan Summary	Summary reflects actual strategy in OM	✅ / ❌	Should be concise and accurate
Red Flag Identification	Flags aggressive assumptions, missing data, or inconsistencies	✅ / ❌	Analyst judgment required
Real-Time Data Accuracy	SOFR or other rates are current and sourced	✅ / ❌	Include source citation
Math Accuracy	Interest cost and other calculations are correct	✅ / ❌	Show formula and result

🧾 2. Output Quality
Criteria	Description	Pass/Fail	Notes
Memo Format	Output is structured like an analyst memo (e.g., Executive Summary, Key Metrics, Commentary)	✅ / ❌	Word or Markdown format
Clarity & Readability	Language is clear, concise, and professional	✅ / ❌	No hallucinations or filler
Source Referencing	Key values include page numbers or section references (if possible)	✅ / ❌	Optional but preferred
Completeness	All requested fields are filled or marked “Not Found”	✅ / ❌	No skipped fields

⚙️ 3. System Behavior
Criteria	Description	Pass/Fail	Notes
File Handling	Can ingest PDF + Excel without errors	✅ / ❌	
Prompt Responsiveness	Understands and executes prompt intent	✅ / ❌	
Error Handling	Gracefully handles missing or malformed data	✅ / ❌	
Performance	Response time is under 2 minutes		

