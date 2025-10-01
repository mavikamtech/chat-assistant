"""LLM gateway abstraction and AWS Bedrock implementation.

Provides a simple, production-ready interface for text completion using
AWS Bedrock (Converse API) with Anthropic Claude models.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

if TYPE_CHECKING:  # pragma: no cover
    from packages.common.models import UserContext


@dataclass
class LLMResult:
    text: str
    model_id: str
    stop_reason: str | None = None
    latency_ms: float | None = None


class LLMGateway(Protocol):
    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        user_context: UserContext | None = None,
    ) -> LLMResult:  # pragma: no cover - interface
        ...


class BedrockGateway:
    """AWS Bedrock Claude via Converse API.

    Environment variables:
        AWS_REGION or AWS_DEFAULT_REGION: Region to use.
        BEDROCK_MODEL_ID: Model ID. Default:
            anthropic.claude-3-5-sonnet-20240620-v1:0
        BEDROCK_TEMPERATURE: float (default 0.2)
        BEDROCK_MAX_TOKENS: int (default 2048)
        BEDROCK_TOP_P: float (default 0.9)
    """

    def __init__(self) -> None:
        """Initialize the Bedrock client and config from environment."""
        self.model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
        )
        self.temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "2048"))
        self.top_p = float(os.getenv("BEDROCK_TOP_P", "0.9"))
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        if not region:
            raise RuntimeError(
                "AWS region not configured. Set AWS_REGION or AWS_DEFAULT_REGION."
            )
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        user_context: UserContext | None = None,
    ) -> LLMResult:
        try:
            messages = []
            if system_prompt:
                messages.append(
                    {
                        "role": "system",
                        "content": [{"text": system_prompt}],
                    }
                )
            # Optionally include user context as metadata in the prompt
            if user_context:
                roles = ",".join(user_context.roles)
                ctx = (
                    f"[user_id={user_context.user_id} roles={roles} "
                    f"tenant={user_context.tenant_id}]\n"
                )
                user_prompt = ctx + prompt
            else:
                user_prompt = prompt

            messages.append(
                {
                    "role": "user",
                    "content": [{"text": user_prompt}],
                }
            )

            resp = self._client.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "temperature": self.temperature,
                    "maxTokens": self.max_tokens,
                    "topP": self.top_p,
                },
            )
        except (BotoCoreError, ClientError) as e:
            # Surface a concise error; leave full details to logs
            raise RuntimeError(f"Bedrock error: {e}") from e

        try:
            content = resp["output"]["message"]["content"][0].get("text")
            stop_reason = resp.get("stopReason")
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Unexpected Bedrock response format") from e

        return LLMResult(
            text=str(content),
            model_id=self.model_id,
            stop_reason=stop_reason,
        )


__all__ = ["LLMGateway", "LLMResult", "BedrockGateway"]
