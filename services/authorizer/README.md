# Lambda Authorizer

AWS Lambda function for API Gateway authorization with Azure AD integration and MNPI access controls.

## Features

- **JWT Validation**: Azure AD and custom JWT token validation
- **RBAC/ABAC**: Role-based and attribute-based access control
- **MNPI Enforcement**: Material Non-Public Information access controls
- **API Gateway Integration**: Standard policy response format
- **Comprehensive Logging**: Structured logging for audit trails

## Installation

```bash
cd services/authorizer
poetry install
```

## Configuration

Set the following environment variables:

```bash
# Azure AD Configuration
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret

# JWT Configuration  
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256

# MNPI Configuration
MNPI_ENFORCEMENT_ENABLED=true
MNPI_DEFAULT_CLASSIFICATION=public
```

## Usage

### Deploy as Lambda Function

```bash
# Package for deployment
poetry build
zip -r authorizer.zip dist/

# Deploy with your infrastructure tool (CDK, Terraform, etc.)
```

### Local Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=authorizer --cov-report=html
```

## API Gateway Integration

Configure API Gateway to use this Lambda as a REQUEST authorizer:

```yaml
AuthorizerType: REQUEST
AuthorizerUri: arn:aws:lambda:region:account:function:mavik-authorizer
IdentitySource: method.request.header.Authorization
AuthorizerResultTtlInSeconds: 300
```

## Token Formats

### Azure AD Token
Standard Azure AD JWT token with required claims:
- `sub` or `oid`: User ID
- `email` or `preferred_username`: User email
- `roles`: User roles array
- `groups`: Optional Azure AD groups

### Custom Token
Custom JWT token for development:
```json
{
  "sub": "user-123",
  "email": "user@example.com",
  "roles": ["analyst"],
  "department": ["real-estate"],
  "exp": 1640995200
}
```

## Roles and Permissions

| Role | Permissions |
|------|-------------|
| `viewer` | Read-only access to deals, documents, reports |
| `analyst` | Full analysis capabilities, MNPI internal access |
| `senior_analyst` | Delete permissions, MNPI confidential access |
| `portfolio_manager` | All deal operations, MNPI restricted access |
| `compliance_officer` | Audit trails, MNPI management |
| `admin` | Full system access |

## MNPI Classifications

| Level | Description | Required Permission |
|-------|-------------|-------------------|
| `public` | Public information | None |
| `internal` | Internal use only | `access_mnpi_internal` |
| `confidential` | Confidential information | `access_mnpi_confidential` |
| `restricted` | Highly sensitive | `access_mnpi_restricted` |

## Development

### Project Structure
```
src/authorizer/
├── __init__.py
├── handler.py          # Lambda entry point
├── jwt_validator.py    # JWT validation logic
└── access_control.py   # RBAC/ABAC implementation

tests/
├── conftest.py         # Test configuration
└── test_authorizer.py  # Unit tests
```

### Adding New Permissions

1. Add permission to `Permission` enum in `access_control.py`
2. Update role mappings in `ROLE_PERMISSIONS`
3. Add permission logic to `_determine_required_permission()` in `handler.py`
4. Add tests for new permission

### Adding New Roles

1. Add role to `Role` enum
2. Define permissions in `ROLE_PERMISSIONS`
3. Update group mapping if using Azure AD groups
4. Add tests for new role

## Monitoring

The authorizer emits structured logs for:
- Authentication attempts (success/failure)
- Authorization decisions (allow/deny)
- MNPI access events (audit trail)
- Configuration errors

Example log entry:
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "INFO",
  "message": "Access granted",
  "user_id": "user-123",
  "email": "user@example.com",
  "resource": "deals/123",
  "permission": "read_deals",
  "mnpi_classification": "internal"
}
```

## Error Handling

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| `AuthenticationError` | 401 | Invalid or expired token |
| `AuthorizationError` | 403 | Insufficient permissions |
| `MNPIAccessDeniedError` | 403 | MNPI access violation |
| `ConfigurationError` | 500 | System configuration issue |

## Security Considerations

- JWT tokens are validated using Azure AD public keys
- MNPI access is logged for audit compliance
- Token caching includes TTL to handle key rotation
- Policy responses include minimal user context
- All authentication failures are logged

## Performance

- Azure AD keys are cached for 1 hour by default
- Policy responses are cacheable by API Gateway
- Authorizer execution time: ~50-200ms typical
- Memory usage: ~64-128MB recommended