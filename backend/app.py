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
            # LangGraph's astream yields dicts with node names as keys
            async for chunk in graph.astream(initial_state):
                # chunk is a dict like {'node_name': state_dict}
                for node_name, state_update in chunk.items():
                    print(f"DEBUG: Node '{node_name}' returned state")

                    if not isinstance(state_update, dict):
                        continue

                    # Stream tool calls
                    if "tool_calls" in state_update and state_update["tool_calls"]:
                        for tool_call in state_update["tool_calls"]:
                            yield f"data: {json.dumps({'type': 'tool', **tool_call})}\n\n"

                    # Stream sections (for pre-screening)
                    if "sections" in state_update and state_update["sections"]:
                        for section in state_update["sections"]:
                            yield f"data: {json.dumps({'type': 'section', **section})}\n\n"

                    # Stream answer (for Q&A)
                    if "answer" in state_update and state_update["answer"]:
                        print(f"DEBUG: Sending answer from node '{node_name}'")
                        yield f"data: {json.dumps({'type': 'answer', 'content': state_update['answer']})}\n\n"

                    # Stream DOCX URL
                    if "docx_url" in state_update and state_update["docx_url"]:
                        yield f"data: {json.dumps({'type': 'artifact', 'url': state_update['docx_url']})}\n\n"

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


