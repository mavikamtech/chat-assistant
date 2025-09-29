# Contributing to Mavik AI

Thank you for your interest in contributing to Mavik AI! This document provides guidelines and information for contributors.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Poetry (Python dependency management)
- Node.js 18+ 
- pnpm (Node.js package manager)
- AWS CLI configured (for cloud deployment)

### Local Development Setup

1. **Clone and install dependencies**:
   ```bash
   git clone https://github.com/mavikamtech/chat-assistant.git
   cd chat-assistant
   poetry install
   cd apps/web && pnpm install
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   export MOCK_AWS=true  # For local development
   ```

3. **Start services** (VS Code recommended):
   - Open workspace in VS Code
   - Run task: "Run All (Local Mock)"
   - Or manually: `F5` → "All Services (Local Mock)"

4. **Verify setup**:
   ```bash
   poetry run python apps/smoke/smoke_orchestrator_local.py
   poetry run python apps/smoke/smoke_tools_local.py
   poetry run python apps/smoke/smoke_report_local.py
   ```

## 🏗️ Architecture Overview

```
User (Web) → API Gateway → Lambda Authorizer (Azure AD) → Lambda Orchestrator (LangGraph)
                                                                      ↓
                            MCP Tools (FastAPI/ECS) ← Bedrock Claude ← Context Assembler
                                     ↓
                     RAG │ Parser │ FinDB │ Web │ Calc │ Report
                      ↓     ↓       ↓      ↓     ↓       ↓
                OpenSearch S3   Aurora  HTTP  Numpy  S3/DOCX
```

### Key Components

- **Orchestrator**: Lambda with LangGraph supervisor pattern
- **MCP Tools**: Microservices implementing Model Context Protocol over WebSocket
- **Agents**: Originations, Strategy, and extensible XYZ agent
- **Data**: OpenSearch (vectors), Aurora (relational), S3 (docs), DynamoDB (audit)

## 📝 Development Workflow

### 1. Create Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed

### 3. Quality Checks
```bash
# Lint and format
poetry run ruff check . --fix
poetry run ruff format .

# Type checking
poetry run mypy .

# Run tests
poetry run pytest -v --cov

# Smoke tests
poetry run python apps/smoke/smoke_orchestrator_local.py
```

### 4. Commit and Push
```bash
git add .
git commit -m "feat: add new feature description"
git push origin feature/your-feature-name
```

### 5. Submit Pull Request
- Create PR against `main` branch
- Ensure CI passes (linting, tests, security scans)
- Request review from team members
- Address feedback and iterate

## 🎯 Coding Standards

### Python
- **Style**: Follow PEP 8, enforced by `ruff`
- **Type Hints**: Required for all functions and classes
- **Docstrings**: Google style for public APIs
- **Error Handling**: Use structured exceptions from `packages/common/errors.py`
- **Async**: Prefer async/await for I/O operations
- **Testing**: Pytest with async support

Example:
```python
from typing import Optional
from packages.common.models import RAGSearchRequest, RAGSearchResponse
from packages.common.errors import ValidationError

async def search_documents(request: RAGSearchRequest) -> RAGSearchResponse:
    \"\"\"Search documents using hybrid vector + BM25 approach.
    
    Args:
        request: Search parameters including query and filters
        
    Returns:
        Search results with chunks and citations
        
    Raises:
        ValidationError: If request parameters are invalid
        TimeoutError: If search exceeds 800ms timeout
    \"\"\"
    if not request.query.strip():
        raise ValidationError("Query cannot be empty")
        
    # Implementation...
```

### TypeScript/Next.js
- **Style**: Prettier formatting, ESLint rules
- **Types**: Strict TypeScript, no `any` types
- **Components**: Functional components with hooks
- **State**: Zustand for global state, React Query for server state
- **Testing**: Vitest for unit tests, Playwright for E2E

Example:
```typescript
interface ChatMessageProps {
  message: Message;
  onCitationClick: (citationId: string) => void;
}

export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="p-4 border rounded-lg">
      {/* Implementation... */}
    </div>
  );
}
```

### Infrastructure (CDK)
- **Language**: Python CDK constructs
- **Naming**: Consistent resource naming with environment suffix
- **Security**: Least privilege IAM, VPC isolation, KMS encryption
- **Monitoring**: CloudWatch alarms for all critical metrics

## 🧪 Testing Guidelines

### Unit Tests
- Cover critical business logic
- Mock external dependencies (AWS services, HTTP calls)
- Use factories for test data
- Aim for >80% coverage

### Integration Tests
- Test MCP tool contracts
- Verify AWS service integrations
- Use localstack for AWS mocking

### Smoke Tests
- End-to-end scenarios in MOCK_AWS mode
- Verify streaming WebSocket functionality
- Test DOCX report generation

### Example Test Structure
```python
# tests/unit/test_rag_search.py
import pytest
from unittest.mock import AsyncMock, patch
from services.mcp_rag.search import hybrid_search

@pytest.fixture
def mock_opensearch():
    return AsyncMock()

@pytest.mark.asyncio
async def test_hybrid_search_with_filters(mock_opensearch):
    \"\"\"Test hybrid search applies filters correctly.\"\"\"
    # Arrange
    request = RAGSearchRequest(
        query="multifamily austin",
        filters={"asset_type": "multifamily", "geo": "austin"},
        topK=5
    )
    
    # Act
    with patch("services.mcp_rag.search.get_opensearch_client", return_value=mock_opensearch):
        results = await hybrid_search(request)
    
    # Assert
    assert len(results.chunks) <= 5
    mock_opensearch.search.assert_called_once()
```

## 📚 Documentation

### Architecture Decision Records (ADRs)
- Document significant architectural decisions
- Follow template in `docs/adr/000-template.md`
- Include context, decision, consequences, alternatives

### API Documentation
- OpenAPI specs auto-generated from FastAPI
- Include examples and error responses
- Document authentication requirements

### Runbooks
- Operational procedures in `docs/runbooks/`
- Incident response playbooks
- Deployment and rollback procedures

## 🔒 Security Guidelines

### Code Security
- No hardcoded secrets or credentials
- Use environment variables for configuration
- Validate all user inputs
- Sanitize outputs to prevent XSS

### Infrastructure Security
- All resources in private VPC
- VPC endpoints for AWS services
- KMS encryption for data at rest
- IAM least privilege principle

### Data Handling
- MNPI (Material Non-Public Information) classification
- Row-level security for financial data
- Audit trail for all operations
- Data retention policies

## 🚢 Deployment Process

### Environments
- **dev**: Auto-deploy from `main` branch
- **staging**: Manual deploy from release candidates
- **prod**: Deploy from tagged releases only

### CI/CD Pipeline
1. **Lint & Test**: Ruff, MyPy, Pytest, Vitest
2. **Security Scan**: Bandit, Safety, Trivy container scans
3. **Build**: Docker images for MCP services
4. **Deploy**: CDK deployment with blue/green for services
5. **Smoke Test**: End-to-end verification
6. **Evaluation**: Support-rate metrics (must be ≥85%)

### Release Process
1. Create release branch from `main`
2. Update version numbers and CHANGELOG
3. Deploy to staging and run full test suite
4. Create Git tag and GitHub release
5. Deploy to production
6. Monitor metrics and error rates

## 🐛 Bug Reports

### Before Submitting
- Search existing issues for duplicates
- Try to reproduce with latest `main` branch
- Gather logs and error messages

### Bug Report Template
```
**Environment**: dev/staging/prod
**Component**: orchestrator/mcp-rag/web/etc
**Version**: Git commit hash

**Description**:
Clear description of the issue

**Steps to Reproduce**:
1. Step one
2. Step two
3. Expected vs actual behavior

**Logs**:
```
Relevant log entries or error messages
```

**Additional Context**:
Screenshots, configuration, related issues
```

## 💡 Feature Requests

### Before Submitting
- Check if feature aligns with product roadmap
- Consider if it can be implemented as extension/plugin
- Provide clear use case and user value

### Feature Request Template
```
**User Story**: As a [user type], I want [functionality] so that [benefit]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Technical Considerations**:
- Impact on existing APIs
- Performance implications
- Security considerations

**Alternatives Considered**:
Other approaches or existing solutions
```

## 🤝 Community

### Communication
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and collaboration

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professional standards

## 📋 Checklist for Contributors

Before submitting a PR, ensure:

- [ ] Code follows style guidelines (ruff, prettier)
- [ ] Type checking passes (mypy, tsc)
- [ ] Tests pass and coverage maintained
- [ ] Smoke tests work in MOCK_AWS mode
- [ ] Documentation updated (README, ADRs, runbooks)
- [ ] Security considerations addressed
- [ ] Breaking changes clearly documented
- [ ] Commit messages follow conventional format

## 🎓 Learning Resources

### Architecture Patterns
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

### Technologies
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [AWS CDK Python Guide](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)

---

Thank you for contributing to Mavik AI! 🚀