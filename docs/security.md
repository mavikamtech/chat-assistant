# Security Model

## Overview

The Mavik AI system implements defense-in-depth security with multiple layers of protection:

1. **Network Security**: Private VPC with VPC endpoints
2. **Data Security**: KMS encryption for all data at rest and in transit
3. **Access Control**: IAM with least-privilege and ABAC
4. **Content Security**: Bedrock Guardrails for AI safety
5. **Audit**: Comprehensive logging and trail

## Network Architecture

```
Internet → WAF → API Gateway → Private VPC
                                    ↓
                            ECS Services (private subnets)
                                    ↓
                            VPC Endpoints → AWS Services
```

### VPC Endpoints
- Bedrock: `com.amazonaws.us-east-1.bedrock-runtime`
- S3: `com.amazonaws.us-east-1.s3`
- OpenSearch: `com.amazonaws.us-east-1.es`
- Secrets Manager: `com.amazonaws.us-east-1.secretsmanager`
- STS: `com.amazonaws.us-east-1.sts`

## Data Classification

| Classification | Examples | Protection Level |
|---|---|---|
| **Public** | Marketing materials | Standard HTTPS |
| **Internal** | System logs, metrics | VPC + KMS |
| **Confidential** | Deal data, analysis | VPC + KMS + ABAC |
| **Restricted** | PII, financial details | VPC + KMS + ABAC + Guardrails |

## Access Control

### Authentication
- **Users**: Cognito User Pool integrated with Azure AD
- **Services**: IAM roles with temporary credentials
- **Developers**: AWS SSO with MFA required

### Authorization (ABAC)
Attribute-based access control using:
- `user:organization` - User's organization
- `resource:dealId` - Deal identifier
- `resource:classification` - Data classification level
- `context:sourceIP` - Request source IP
- `context:time` - Request timestamp

### IAM Policies
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::mavik-deals/*",
      "Condition": {
        "StringEquals": {
          "s3:ExistingObjectTag/organization": "${aws:PrincipalTag/organization}"
        }
      }
    }
  ]
}
```

## Encryption

### At Rest
- **S3**: SSE-KMS with customer-managed keys
- **Aurora**: Encryption enabled with KMS
- **OpenSearch**: Encryption at rest with KMS
- **DynamoDB**: Encryption with AWS managed keys

### In Transit
- **HTTPS/TLS 1.3**: All external communications
- **VPC Endpoints**: Private AWS service access
- **WebSockets**: WSS (WebSocket Secure) only

## Content Security

### Bedrock Guardrails
- **PII Detection**: Automatic redaction of sensitive data
- **Content Filtering**: Block harmful or inappropriate content
- **Topic Filtering**: Prevent off-topic conversations
- **Word Filtering**: Block specific terms or phrases

### Input Validation
- **Schema Validation**: All inputs validated against JSON Schema
- **Size Limits**: Maximum payload sizes enforced
- **Rate Limiting**: Per-user and per-service rate limits

## Monitoring & Compliance

### Audit Trail
All actions logged with:
- User identity and session
- Resource accessed
- Action performed
- Timestamp and source IP
- Request/response data (sanitized)

### Security Monitoring
- **CloudTrail**: All AWS API calls
- **GuardDuty**: Threat detection
- **Security Hub**: Centralized findings
- **Custom Metrics**: Application-level security events

### Compliance
- **SOC 2**: Security, availability, and confidentiality
- **GDPR**: Data protection and privacy rights
- **Industry Standards**: Following real estate data handling best practices

## Incident Response

### Security Event Classification
1. **Low**: Minor configuration issues
2. **Medium**: Unauthorized access attempts
3. **High**: Data exposure or system compromise
4. **Critical**: Active data breach or system compromise

### Response Team
- **Security Lead**: Overall incident coordination
- **Engineering Lead**: Technical investigation and remediation
- **Legal/Compliance**: Regulatory notification requirements
- **Communications**: Internal and external communications

### Response Procedures
1. **Detection**: Automated alerts and manual reporting
2. **Containment**: Isolate affected systems
3. **Investigation**: Determine scope and impact
4. **Remediation**: Fix vulnerabilities and restore service
5. **Recovery**: Validate system integrity
6. **Lessons Learned**: Update procedures and controls

## Security Testing

### Regular Testing
- **Quarterly**: Penetration testing by third-party
- **Monthly**: Vulnerability scanning
- **Weekly**: Security configuration review
- **Daily**: Automated security tests in CI/CD

### Code Security
- **SAST**: Static analysis with Bandit (Python)
- **Dependency Scanning**: Check for known vulnerabilities
- **Container Scanning**: Trivy for container images
- **Infrastructure**: CDK NAG for infrastructure security
