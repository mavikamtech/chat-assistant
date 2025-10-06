import boto3
import json
import os
from typing import AsyncIterator, Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class BedrockClient:
    def __init__(self, model_id: Optional[str] = None):
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        # Allow override, otherwise use default from env
        self.model_id = model_id or os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
        self.haiku_model_id = os.getenv('BEDROCK_MODEL_ID_HAIKU', 'us.anthropic.claude-3-5-haiku-20241022-v1:0')

    async def invoke_claude(self, prompt: str, system: Optional[str] = None) -> str:
        """Invoke Claude for non-streaming responses"""

        messages = [{"role": "user", "content": prompt}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": messages,
            "temperature": 0.7
        }

        if system:
            body["system"] = system

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )

        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']


    async def invoke_claude_streaming(
        self,
        prompt: str,
        system: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Invoke Claude with streaming responses"""

        messages = [{"role": "user", "content": prompt}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": messages,
            "temperature": 0.7
        }

        if system:
            body["system"] = system

        response = self.client.invoke_model_with_response_stream(
            modelId=self.model_id,
            body=json.dumps(body)
        )

        stream = response.get('body')
        if stream:
            for event in stream:
                chunk = event.get('chunk')
                if chunk:
                    chunk_obj = json.loads(chunk.get('bytes').decode())

                    if chunk_obj['type'] == 'content_block_delta':
                        delta = chunk_obj.get('delta', {})
                        if delta.get('type') == 'text_delta':
                            yield delta.get('text', '')

def parse_json(text: str) -> Dict[str, Any]:
    """Parse JSON from Claude's response, handling markdown code blocks"""

    # Try to extract JSON from markdown code blocks
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        text = text[start:end].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        text = text[start:end].strip()

    return json.loads(text)

# Global instances
bedrock_client = BedrockClient()  # Sonnet for analysis
bedrock_haiku_client = BedrockClient(model_id=os.getenv('BEDROCK_MODEL_ID_HAIKU'))  # Haiku for lightweight tasks

async def invoke_claude(prompt: str, system: Optional[str] = None, use_haiku: bool = False) -> str:
    """
    Invoke Claude with optional Haiku for lightweight tasks

    Args:
        prompt: User prompt
        system: System instructions
        use_haiku: If True, use Haiku (faster, cheaper); otherwise use Sonnet (more accurate)
    """
    client = bedrock_haiku_client if use_haiku else bedrock_client
    return await client.invoke_claude(prompt, system)

async def invoke_claude_streaming(prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
    """Always use Sonnet for streaming (document analysis, pre-screening)"""
    async for chunk in bedrock_client.invoke_claude_streaming(prompt, system):
        yield chunk
