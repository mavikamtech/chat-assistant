"""AWS Bedrock client for AI model interactions."""

import json
import logging
from typing import Any, Dict, List, Optional, AsyncIterator
from contextlib import asynccontextmanager

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..common.errors import (
    BedrockError,
    BedrockModelNotFoundError,
    BedrockTokenLimitError,
    AWSServiceError,
)

logger = logging.getLogger(__name__)


class BedrockClient:
    """AWS Bedrock client with retry logic and streaming support."""
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize Bedrock client.
        
        Args:
            region_name: AWS region for Bedrock
            aws_access_key_id: Optional explicit AWS credentials
            aws_secret_access_key: Optional explicit AWS credentials
        """
        self.region_name = region_name
        
        try:
            session_kwargs = {"region_name": region_name}
            if aws_access_key_id and aws_secret_access_key:
                session_kwargs.update({
                    "aws_access_key_id": aws_access_key_id,
                    "aws_secret_access_key": aws_secret_access_key,
                })
            
            self.session = boto3.Session(**session_kwargs)
            self.client = self.session.client("bedrock-runtime")
            self.pricing_client = self.session.client("bedrock")
            
        except NoCredentialsError as e:
            raise AWSServiceError(f"AWS credentials not found: {e}")
        except Exception as e:
            raise AWSServiceError(f"Failed to initialize Bedrock client: {e}")
    
    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def invoke_model(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        top_p: float = 1.0,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Invoke a Bedrock model with messages.
        
        Args:
            model_id: Bedrock model identifier
            messages: Conversation messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            system_prompt: Optional system prompt
            **kwargs: Additional model parameters
            
        Returns:
            Model response dictionary
            
        Raises:
            BedrockError: For Bedrock-specific errors
            BedrockModelNotFoundError: If model not found
            BedrockTokenLimitError: If token limit exceeded
        """
        try:
            # Format request based on model family
            if model_id.startswith("anthropic.claude"):
                body = self._format_claude_request(
                    messages, max_tokens, temperature, top_p, system_prompt
                )
            elif model_id.startswith("amazon.titan"):
                body = self._format_titan_request(
                    messages, max_tokens, temperature, top_p
                )
            else:
                raise BedrockError(f"Unsupported model: {model_id}")
            
            logger.info(f"Invoking Bedrock model: {model_id}")
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body).encode(),
            )
            
            response_body = json.loads(response["body"].read())
            logger.info(f"Bedrock response received, tokens: {response_body.get('usage', {})}")
            
            return response_body
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            
            if error_code == "ResourceNotFoundException":
                raise BedrockModelNotFoundError(f"Model not found: {model_id}")
            elif error_code == "ValidationException" and "token" in error_msg.lower():
                raise BedrockTokenLimitError(f"Token limit exceeded: {error_msg}")
            else:
                raise BedrockError(f"Bedrock API error: {error_msg}")
                
        except Exception as e:
            raise BedrockError(f"Unexpected error invoking model: {e}")
    
    @asynccontextmanager
    async def invoke_model_stream(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        top_p: float = 1.0,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream model response chunks.
        
        Args:
            model_id: Bedrock model identifier
            messages: Conversation messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            system_prompt: Optional system prompt
            **kwargs: Additional model parameters
            
        Yields:
            Response chunks as they arrive
            
        Raises:
            BedrockError: For streaming errors
        """
        try:
            # Format request
            if model_id.startswith("anthropic.claude"):
                body = self._format_claude_request(
                    messages, max_tokens, temperature, top_p, system_prompt
                )
            else:
                raise BedrockError(f"Streaming not supported for model: {model_id}")
            
            logger.info(f"Starting Bedrock stream: {model_id}")
            response = self.client.invoke_model_with_response_stream(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body).encode(),
            )
            
            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        chunk_data = json.loads(chunk.get("bytes").decode())
                        yield chunk_data
                        
        except Exception as e:
            raise BedrockError(f"Streaming error: {e}")
    
    def _format_claude_request(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        temperature: float,
        top_p: float,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Format request for Claude models."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        
        if system_prompt:
            body["system"] = system_prompt
            
        return body
    
    def _format_titan_request(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> Dict[str, Any]:
        """Format request for Titan models."""
        # Convert messages to single prompt for Titan
        prompt = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in messages
        ])
        
        return {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": temperature,
                "topP": top_p,
            }
        }
    
    async def get_embeddings(
        self,
        text: str,
        model_id: str = "amazon.titan-embed-text-v2:0",
    ) -> List[float]:
        """Generate embeddings for text.
        
        Args:
            text: Input text
            model_id: Embedding model identifier
            
        Returns:
            Embedding vector
            
        Raises:
            BedrockError: For embedding errors
        """
        try:
            body = {"inputText": text}
            
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body).encode(),
            )
            
            response_body = json.loads(response["body"].read())
            return response_body["embedding"]
            
        except Exception as e:
            raise BedrockError(f"Embedding generation failed: {e}")
    
    async def list_foundation_models(self) -> List[Dict[str, Any]]:
        """List available foundation models.
        
        Returns:
            List of model information dictionaries
        """
        try:
            response = self.pricing_client.list_foundation_models()
            return response.get("modelSummaries", [])
        except Exception as e:
            raise BedrockError(f"Failed to list models: {e}")
    
    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model information dictionary
        """
        try:
            response = self.pricing_client.get_foundation_model(modelIdentifier=model_id)
            return response.get("modelDetails", {})
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                raise BedrockModelNotFoundError(f"Model not found: {model_id}")
            raise BedrockError(f"Failed to get model info: {e}")
        except Exception as e:
            raise BedrockError(f"Unexpected error getting model info: {e}")