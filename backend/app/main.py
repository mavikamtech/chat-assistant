import os
import uuid
import hashlib
from pathlib import Path
from typing import List, Optional

# ADD THIS
from dotenv import load_dotenv

# Load .env from the backend folder (adjust path if yours is different)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # <-- must run before os.getenv calls

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import boto3
from botocore.exceptions import ClientError


# -------------------- App & CORS --------------------
app = FastAPI(title="Mavik Chat Assistant API", version="0.1.0")

default_origins = "http://127.0.0.1:3000,http://localhost:3000"
origins = os.getenv("CORS_ALLOW_ORIGINS", default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Config --------------------
UPLOAD_DIR = Path(os.getenv("LOCAL_UPLOADS_DIR", Path(__file__).resolve().parent.parent / "uploads"))
MAX_FILES = int(os.getenv("MAX_FILES", "15"))
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(25 * 1024 * 1024)))  # 25 MB

ALLOWED_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv"}
ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    "text/plain",
    "text/csv",
}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- S3 config ---
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_UPLOADS_BUCKET = os.getenv("S3_UPLOADS_BUCKET")

def s3_client():
    return boto3.client("s3", region_name=AWS_REGION)

# -------------------- Models --------------------
class ChatRequest(BaseModel):
    message: str
    top_k: int = 4

class Citation(BaseModel):
    doc_id: str
    title: str
    page: Optional[int] = None

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = []

# NEW: presign models
class PresignRequest(BaseModel):
    filename: str
    content_type: str

class PresignResponse(BaseModel):
    url: str
    fields: dict
    key: str

# -------------------- Health --------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}

# -------------------- Upload (local mode) --------------------
@app.post("/upload")
async def upload_file(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=413, detail=f"Too many files. Limit is {MAX_FILES}.")

    saved = []
    for up in files:
        ext = Path(up.filename).suffix.lower()
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail=f"Extension {ext} not allowed.")
        if up.content_type and up.content_type not in ALLOWED_MIMES:
            raise HTTPException(status_code=400, detail=f"MIME {up.content_type} not allowed.")

        safe_name = Path(up.filename).name
        target_name = f"{uuid.uuid4().hex}{ext}"
        target_path = UPLOAD_DIR / target_name

        hasher = hashlib.sha256()
        total = 0
        try:
            with target_path.open("wb") as f:
                while True:
                    chunk = await up.read(1024 * 1024)  # 1 MB
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        try:
                            target_path.unlink(missing_ok=True)
                        except TypeError:
                            if target_path.exists():
                                target_path.unlink()
                        raise HTTPException(status_code=413, detail=f"File {safe_name} exceeds {MAX_FILE_BYTES} bytes.")
                    hasher.update(chunk)
                    f.write(chunk)
        finally:
            await up.close()

        saved.append({
            "original_name": safe_name,
            "stored_name": target_name,
            "bytes": total,
            "sha256": hasher.hexdigest(),
            "content_type": up.content_type,
        })

    return JSONResponse(content={"uploaded": saved})

# -------------------- NEW: Presigned S3 upload --------------------
@app.post("/upload/presign", response_model=PresignResponse)
def get_presigned_post(req: PresignRequest):
    if not S3_UPLOADS_BUCKET:
        raise HTTPException(status_code=500, detail="S3 bucket not configured")

    ext = Path(req.filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Extension {ext} not allowed.")
    if req.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail=f"MIME {req.content_type} not allowed.")

    key = f"uploads/{uuid.uuid4().hex}{ext}"
    try:
        resp = s3_client().generate_presigned_post(
            Bucket=S3_UPLOADS_BUCKET,
            Key=key,
            Fields={"Content-Type": req.content_type},
            Conditions=[
                {"Content-Type": req.content_type},
                ["content-length-range", 1, MAX_FILE_BYTES],
            ],
            ExpiresIn=600,
        )
        return PresignResponse(url=resp["url"], fields=resp["fields"], key=key)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------- Chat (stub) --------------------
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    return ChatResponse(
        answer=f"Echo: {req.message}",
        citations=[Citation(doc_id="doc-123", title="Sample Policy.pdf", page=2)],
    )
