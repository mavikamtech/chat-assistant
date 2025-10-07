# Quick Start Guide

## Prerequisites
- Python 3.11+ installed
- Node.js 18+ installed
- AWS Account with Bedrock access

## Setup Steps

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**If you get errors**, install packages individually:
```bash
pip install fastapi uvicorn python-multipart boto3 pydantic python-dotenv python-docx opensearch-py tavily-python pytest pytest-asyncio httpx
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your AWS credentials:
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# AWS_REGION=us-east-1
```

### 3. Run Backend (without Docker)

```bash
cd backend
python run.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Install and Run Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

You should see:
```
ready - started server on 0.0.0.0:3000
```

### 5. Open the App

Go to: http://localhost:3000

## Testing the App

### Test 1: Simple Question (No PDF)
1. Type: "What is DSCR?"
2. Click "Send"
3. You should get an AI response

### Test 2: Financial Calculation
1. Type: "Calculate DSCR for NOI of $2.5M and debt service of $1.8M"
2. Click "Send"
3. You should see: "DSCR = 2,500,000 / 1,800,000 = 1.39x"

### Test 3: PDF Upload (requires real PDF)
1. Click "Attach PDF"
2. Select an offering memorandum PDF
3. Type your analysis prompt
4. Click "Send"
5. Wait for the analysis sections to stream

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Install missing dependencies
pip install langgraph langchain langchain-core
```

### Frontend won't start
```bash
# Clear node_modules and reinstall
rm -rf node_modules
npm install
```

### AWS Credentials Error
Make sure your `.env` file has valid AWS credentials:
```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

### Module Import Errors
Make sure you're running from the correct directory:
```bash
# Always run from backend directory
cd backend
python run.py
```

## Minimal Test (No AWS Required)

To test the basic setup without AWS:

1. Comment out the AWS-dependent imports in `backend/app.py`:
```python
# graph = create_graph()  # Comment this line
```

2. Start the server:
```bash
cd backend
python run.py
```

3. Test health endpoint:
```bash
curl http://localhost:8000/health
```

You should see: `{"status":"ok","service":"Mavik AI Assistant"}`
