"""
Detailed test showing actual PDF analysis results
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("=" * 70)
    print("DETAILED PDF ANALYSIS TEST")
    print("=" * 70)

    # Get latest PDF from S3
    import boto3
    s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-2'))

    response = s3.list_objects_v2(Bucket='mavik-uploads', Prefix='uploads/', MaxKeys=5)
    pdfs = [o for o in response.get('Contents', []) if o['Key'].endswith('.pdf')]

    if not pdfs:
        print("ERROR: No PDFs found in S3")
        return

    latest = sorted(pdfs, key=lambda x: x['LastModified'], reverse=True)[0]
    file_url = f"s3://mavik-uploads/{latest['Key']}"

    print(f"\nPDF: {latest['Key'].split('/')[-1]}")
    print(f"Size: {latest['Size'] / 1024:.1f} KB")
    print(f"Uploaded: {latest['LastModified']}")
    print()

    # Initialize state with a realistic message
    state = {
        "conversation_id": "test-detailed-123",
        "user_message": "Please analyze this commercial real estate offering memorandum and provide a comprehensive pre-screening analysis including sponsor analysis, market positioning, financial underwriting, and investment recommendation.",
        "file_url": file_url,
        "tool_calls": [],
        "intent": "",
        "requires_pdf": False,
        "selected_tools": [],
        "pdf_text": None,
        "pdf_tables": [],
        "rag_results": [],
        "web_results": [],
        "finance_calcs": {},
        "sections": None,
        "answer": None,
        "docx_url": None
    }

    # Run orchestrator
    from orchestrator.graph import create_graph
    graph = create_graph()

    print("Processing with orchestrator...")
    print("-" * 70)

    final_state = None

    try:
        async for chunk in graph.astream(state):
            for node_name, state_update in chunk.items():
                # Only show key milestones
                if node_name == "extract_pdf" and "pdf_text" in state_update:
                    print(f"[extract_pdf] Extracted {len(state_update['pdf_text'])} chars")
                elif node_name == "search_web" and "web_results" in state_update:
                    print(f"[search_web] Found {len(state_update['web_results'])} web results")
                elif node_name == "generate" and "sections" in state_update:
                    print(f"[generate] Generated {len(state_update['sections'])} sections")
                elif node_name == "create_docx" and "docx_url" in state_update:
                    print(f"[create_docx] Report created")

                final_state = state_update

        print("-" * 70)
        print()

        if not final_state:
            print("ERROR: No final state")
            return

        # Show detailed results
        print("=" * 70)
        print("ANALYSIS RESULTS")
        print("=" * 70)

        # 1. PDF Extraction
        print("\n[1] PDF EXTRACTION")
        print(f"    Text length: {len(final_state.get('pdf_text', ''))} characters")
        print(f"    Tables found: {len(final_state.get('pdf_tables', []))}")
        print(f"\n    Sample text (first 300 chars):")
        print("    " + "-" * 66)
        sample = final_state.get('pdf_text', '')[:300].replace('\n', '\n    ')
        print(f"    {sample}")
        print("    " + "-" * 66)

        # 2. Web Research
        web_results = final_state.get('web_results', [])
        print(f"\n[2] WEB RESEARCH")
        print(f"    Sources found: {len(web_results)}")
        for i, result in enumerate(web_results[:3], 1):
            print(f"    {i}. {result.get('title', 'No title')}")
            print(f"       URL: {result.get('url', 'No URL')}")

        # 3. Sections Generated
        sections = final_state.get('sections', [])
        print(f"\n[3] PRE-SCREENING SECTIONS")
        print(f"    Total sections: {len(sections)}")
        print()
        for i, section in enumerate(sections, 1):
            title = section.get('title', 'Unknown')
            content = section.get('content', '')
            content_preview = content[:150] + "..." if len(content) > 150 else content
            print(f"    Section {i}: {title}")
            print(f"    {content_preview}")
            print()

        # 4. DOCX Report
        docx_url = final_state.get('docx_url')
        if docx_url:
            print(f"[4] WORD DOCUMENT")
            print(f"    Download URL: {docx_url[:80]}...")
            print(f"    Valid for: 7 days")
        else:
            print(f"[4] WORD DOCUMENT")
            print(f"    Status: Not generated (pre_screen intent required)")

        # 5. Tool Performance
        tool_calls = final_state.get('tool_calls', [])
        completed = [tc for tc in tool_calls if tc.get('status') == 'completed']
        print(f"\n[5] TOOL PERFORMANCE")
        for tc in completed:
            tool_name = tc.get('tool', 'unknown')
            duration = tc.get('duration_ms', 0)
            summary = tc.get('summary', '')
            print(f"    {tool_name}: {duration}ms - {summary}")

        print("\n" + "=" * 70)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 70)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
