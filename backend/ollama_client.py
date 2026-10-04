"""Thin async client for the local Ollama HTTP API (chat + streaming)."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


class OllamaClient:
    def __init__(self, host: str, model: str, temperature: float = 0.7, num_ctx: int = 8192):
        self.host = host.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.num_ctx = num_ctx

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yields assistant text chunks as they arrive from Ollama's /api/chat endpoint."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
            },
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self.host}/api/chat", json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise RuntimeError(
                        f"Ollama request failed ({resp.status_code}): {body.decode(errors='ignore')}"
                    )
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if error := data.get("error"):
                        raise RuntimeError(f"Ollama error: {error}")
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break

    async def is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.host}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
