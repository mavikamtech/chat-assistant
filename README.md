# Chat Assistant

A secure, production-ready GenAI chat assistant for Mavik, leveraging AWS Bedrock and Retrieval-Augmented Generation (RAG) to provide contextual answers from uploaded documents, internal databases, emails, and third-party data.

## Features
- Secure document upload (PDF, Word, Excel, PowerPoint)
- RAG-based querying using AWS Bedrock
- Integration with portfolio (SSOT) database
- Multi-turn chat with memory
- SSO authentication (Okta/Azure AD)
- Audit logging and compliance (SOC2, ISO 27001)
- Modular architecture for future integrations (emails, 3rd party data, real-time market data)

## Project Structure
```
chat-assistant/
│
├── backend/         # Backend API and services
├── frontend/        # Frontend (React/Streamlit)
├── infra/           # Infrastructure as Code (Terraform/CDK)
├── .env.example     # Example environment variables
├── README.md
└── .gitignore
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- AWS account with Bedrock access
- SSO provider (Okta/Azure AD)

### Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/mavikamtech/chat-assistant.git
   ```
2. Install backend dependencies:
   ```sh
   cd backend
   pip install -r requirements.txt
   ```
3. Install frontend dependencies:
   ```sh
   cd ../frontend
   npm install
   ```
4. Set up environment variables (see `.env.example`).
5. Run backend and frontend locally.

## Contributing
- Create a feature branch for your changes.
- Open a pull request for review.

## License
Proprietary. All rights reserved.
