from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import boto3
import uuid
import json
from orchestrator.graph import create_graph
from models import ChatRequest, ChatResponse

app = FastAPI(title="Mavik AI Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://ai.mavik-ssot.com",
        "https://ai.mavik-ssot.com",
        "http://mavik-ai-alb-1935869446.us-east-2.elb.amazonaws.com",
        "https://mavik-ai-alb-1935869446.us-east-2.elb.amazonaws.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize S3 client and graph
s3_client = boto3.client('s3')
graph = create_graph()

@app.post("/api/chat")
async def chat_endpoint(
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    conversation_id: Optional[str] = Form(None)
):
    """
    Main chat endpoint. Handles both text-only and file upload requests.
    Returns streaming response.
    """

    # Upload file to S3 if provided
    file_url = None
    if file:
        try:
            file_key = f"uploads/{uuid.uuid4()}/{file.filename}"

            # Upload with proper settings for Textract access
            s3_client.upload_fileobj(
                file.file,
                'mavik-uploads',
                file_key,
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'ServerSideEncryption': 'AES256'
                }
            )

            file_url = f"s3://mavik-uploads/{file_key}"
            print(f"DEBUG: File uploaded to {file_url}")

            # Verify the file exists in S3
            try:
                s3_client.head_object(Bucket='mavik-uploads', Key=file_key)
                print(f"DEBUG: Verified file exists in S3: {file_key}")
            except Exception as e:
                print(f"ERROR: File verification failed: {e}")

        except Exception as e:
            print(f"ERROR uploading file to S3: {e}")
            import traceback
            traceback.print_exc()
            file_url = None

    # Run orchestrator
    initial_state = {
        "conversation_id": conversation_id or str(uuid.uuid4()),
        "user_message": message,
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

    async def generate():
        try:
            print(f"DEBUG: ===== STARTING NEW REQUEST =====")
            print(f"DEBUG: Message: {message[:100]}...")
            print(f"DEBUG: File URL: {file_url}")

            # Use astream to get updates as each node completes (prevents HTTP timeout)
            print(f"DEBUG: Calling graph.astream()")

            # Track tool calls and final state components
            tool_calls_sent = set()
            final_state = None

            async for event in graph.astream(initial_state):
                print(f"DEBUG: Stream event received: {list(event.keys())}")

                # Get the latest state from the event
                for node_name, node_state in event.items():
                    final_state = node_state
                    print(f"DEBUG: Node '{node_name}' completed")

                    # Stream new tool calls as they're added
                    if "tool_calls" in node_state:
                        for i, tool_call in enumerate(node_state["tool_calls"]):
                            tool_key = f"{tool_call.get('tool', 'unknown')}_{i}"
                            if tool_key not in tool_calls_sent:
                                print(f"DEBUG: Streaming tool call: {tool_call}")
                                yield f"data: {json.dumps({'type': 'tool', **tool_call})}\n\n"
                                tool_calls_sent.add(tool_key)

                    # Send heartbeat to keep connection alive during long operations
                    yield f"data: {json.dumps({'type': 'progress', 'node': node_name})}\n\n"

            print(f"DEBUG: Graph execution completed")

            # Stream final outputs if present
            if final_state:
                # Stream sections (for pre-screening)
                if "sections" in final_state and final_state["sections"]:
                    print(f"DEBUG: Streaming {len(final_state['sections'])} sections")
                    for section in final_state["sections"]:
                        yield f"data: {json.dumps({'type': 'section', **section})}\n\n"

                # Stream answer (for Q&A)
                if "answer" in final_state and final_state["answer"]:
                    print(f"DEBUG: Streaming answer (length: {len(final_state['answer'])} chars)")
                    yield f"data: {json.dumps({'type': 'answer', 'content': final_state['answer']})}\n\n"

                # Stream DOCX URL
                if "docx_url" in final_state and final_state["docx_url"]:
                    print(f"DEBUG: Streaming docx_url")
                    yield f"data: {json.dumps({'type': 'artifact', 'url': final_state['docx_url']})}\n\n"

            print(f"DEBUG: Sending done event")
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            print(f"ERROR in generate: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Mavik AI Assistant"}

@app.get("/")
async def root():
    return {
        "service": "Mavik AI Assistant",
        "version": "1.0.0",
        "endpoints": {
            "/api/chat": "Main chat endpoint (POST)",
            "/health": "Health check (GET)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


