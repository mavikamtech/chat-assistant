"""Shared packages for Mavik AI system."""

# Import key modules for easy access
from .common import *
from .config import Settings, get_settings
from .aws_clients import (
    BedrockClient,
    S3Client,
    DynamoDBClient,
    RDSClient,
    OpenSearchClient,
    TextractClient,
)

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    
    # AWS Clients
    "BedrockClient",
    "S3Client", 
    "DynamoDBClient",
    "RDSClient",
    "OpenSearchClient",
    "TextractClient",
    
    # Common models and errors (imported via *)
]
