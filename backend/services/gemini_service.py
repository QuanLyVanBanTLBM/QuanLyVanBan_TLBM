import io
import json
import time
import base64
import urllib.request
import urllib.error
from typing import Any, List, Optional
from PIL import Image

from llama_index.core.llms.custom import CustomLLM
from llama_index.core.llms import CompletionResponse, CompletionResponseGen, LLMMetadata
from llama_index.core.base.embeddings.base import BaseEmbedding
from pydantic import Field

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
class GeminiRESTLLM(CustomLLM):
    api_key: str = Field(description="Gemini API key")
    model_name: str = Field(default="gemini-3.8-flash")
    timeout_sec: float = Field(default=60.0)

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(model_name=self.model_name)

    def _get_models_to_try(self) -> List[str]:
        return [self.model_name]

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        models = self._get_models_to_try()
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        body = json.dumps(payload).encode("utf-8")
        last_status = None

        for model in models:
            url = f"{GEMINI_BASE_URL}/models/{model}:generateContent"
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
                method="POST"
            )
            # Try up to 2 times for each model
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            text = "".join(p.get("text", "") for p in parts)
                            return CompletionResponse(text=text)
                        return CompletionResponse(text="")
                except urllib.error.HTTPError as e:
                    last_status = e.code
                    # If 503 or 429, wait briefly or try next model
                    if e.code in (503, 429):
                        time.sleep(1.0)
                        continue
                    # 404 or other error: immediately try next model
                    break
                except Exception:
                    time.sleep(0.5)

        raise RuntimeError(f"Gemini generation failed for configured model (HTTP {last_status}).")

    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        res = self.complete(prompt, **kwargs)
        yield res


class GeminiRESTEmbedding(BaseEmbedding):
    api_key: str = Field(description="Gemini API key")
    model_name: str = Field(default="models/gemini-embedding-001")
    timeout_sec: float = Field(default=30.0)

    def _normalize_model_name(self) -> str:
        name = self.model_name
        if not name.startswith("models/"):
            name = f"models/{name}"
        return name

    def _get_text_embedding(self, text: str) -> List[float]:
        model = self._normalize_model_name()
        url = f"{GEMINI_BASE_URL}/{model}:embedContent"
        payload = {"model": model, "content": {"parts": [{"text": text or " "}]}}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST"
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["embedding"]["values"]
            except urllib.error.HTTPError as e:
                if e.code in (503, 429) and attempt < 2:
                    time.sleep(1.0)
                    continue
                raise
            except Exception:
                if attempt < 2:
                    time.sleep(0.5)
                    continue
                raise
        return []

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        # Batch in chunks of 50 to stay within limits
        batch_size = 50
        all_embeddings = []
        model = self._normalize_model_name()
        url = f"{GEMINI_BASE_URL}/{model}:batchEmbedContents"

        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            payload = {
                "requests": [
                    {"model": model, "content": {"parts": [{"text": t or " "}]}}
                    for t in chunk
                ]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
                method="POST"
            )
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=self.timeout_sec * 2) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        embeddings = [item["values"] for item in data.get("embeddings", [])]
                        all_embeddings.extend(embeddings)
                        break
                except urllib.error.HTTPError as e:
                    if e.code in (503, 429) and attempt < 2:
                        time.sleep(1.5)
                        continue
                    # Fallback to single requests
                    for t in chunk:
                        all_embeddings.append(self._get_text_embedding(t))
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(1.0)
                        continue
                    for t in chunk:
                        all_embeddings.append(self._get_text_embedding(t))
                    break

        return all_embeddings

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._get_text_embedding(query)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_text_embedding(query)


def call_gemini_vision(
    image: Image.Image,
    prompt: str,
    api_key: str,
    model_name: str = "gemini-3.8-flash",
    timeout_sec: float = 60.0
) -> str:
    """Gọi Gemini Multimodal Vision để đọc công thức LaTeX, bảng biểu, ảnh."""
    if not api_key:
        return ""

    buffer = io.BytesIO()
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(buffer, format="JPEG", quality=90)
    b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    models = [model_name]

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
            ]
        }]
    }
    body = json.dumps(payload).encode("utf-8")

    for model in models:
        url = f"{GEMINI_BASE_URL}/models/{model}:generateContent"
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST"
        )
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        return "".join(p.get("text", "") for p in parts).strip()
                    return ""
            except urllib.error.HTTPError as e:
                if e.code in (503, 429):
                    time.sleep(1.0)
                    continue
                break
            except Exception as e:
                time.sleep(0.5)

    return ""
