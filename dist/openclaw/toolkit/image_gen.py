#!/usr/bin/env python3
"""
AI image generation module for WeWrite.

Supports multiple providers via a simple abstraction:
  - doubao-seedream (Volcengine Ark) — default, good for Chinese prompts
  - openai (DALL-E 3) — broad availability
  - gemini (Google Gemini Imagen) — multimodal image generation
  - dashscope (Alibaba Tongyi Wanxiang) — good for Chinese prompts
  - minimax — Chinese provider
  - replicate — open-source models
  - azure_openai — Azure-hosted DALL-E
  - openrouter — multi-model proxy
  - jimeng (ByteDance) — good for Chinese prompts
  - Custom providers via ImageProvider base class

Usage as CLI:
    python3 image_gen.py --prompt "描述" --output cover.png
    python3 image_gen.py --prompt "描述" --output cover.png --size cover
    python3 image_gen.py --prompt "描述" --output cover.png --provider gemini

Usage as module:
    from image_gen import generate_image
    path = generate_image("prompt text", "output.png", size="cover")
"""

import abc
import argparse
import base64
import hashlib
import hmac
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

# --- Config ---

def _load_config() -> dict:
    """Load config via unified config module, with fallback to local search."""
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent))
        from config import load_config
        return load_config()
    except ImportError:
        for p in [
            Path(__file__).parent.parent / "config.yaml",
            Path(__file__).parent / "config.yaml",
            Path.home() / ".config" / "wewrite" / "config.yaml",
        ]:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        return {}


# --- Size presets ---

_DEFAULT = "1792x1024"
_DEFAULT_V = "1024x1792"
_DEFAULT_SQ = "1024x1024"

SIZE_PRESETS = {
    "cover": {
        "doubao": "2952x1256", "openai": _DEFAULT, "gemini": _DEFAULT,
        "dashscope": _DEFAULT, "minimax": _DEFAULT, "replicate": _DEFAULT,
        "azure_openai": _DEFAULT, "openrouter": _DEFAULT, "jimeng": _DEFAULT,
    },
    "article": {
        "doubao": "2560x1440", "openai": _DEFAULT, "gemini": _DEFAULT,
        "dashscope": _DEFAULT, "minimax": _DEFAULT, "replicate": _DEFAULT,
        "azure_openai": _DEFAULT, "openrouter": _DEFAULT, "jimeng": _DEFAULT,
    },
    "vertical": {
        "doubao": "1088x2560", "openai": _DEFAULT_V, "gemini": _DEFAULT_V,
        "dashscope": _DEFAULT_V, "minimax": _DEFAULT_V, "replicate": _DEFAULT_V,
        "azure_openai": _DEFAULT_V, "openrouter": _DEFAULT_V, "jimeng": _DEFAULT_V,
    },
    "square": {
        "doubao": "2048x2048", "openai": _DEFAULT_SQ, "gemini": _DEFAULT_SQ,
        "dashscope": _DEFAULT_SQ, "minimax": _DEFAULT_SQ, "replicate": _DEFAULT_SQ,
        "azure_openai": _DEFAULT_SQ, "openrouter": _DEFAULT_SQ, "jimeng": _DEFAULT_SQ,
    },
}

MAX_FILE_SIZE = 5 * 1024 * 1024


class ImageProvider(abc.ABC):
    """Base class for image generation providers."""

    @abc.abstractmethod
    def generate(self, prompt: str, size: str) -> bytes:
        ...

    def resolve_size(self, preset: str) -> str:
        provider_key = self.provider_key
        if preset in SIZE_PRESETS:
            return SIZE_PRESETS[preset].get(provider_key, list(SIZE_PRESETS[preset].values())[0])
        return preset

    @property
    @abc.abstractmethod
    def provider_key(self) -> str:
        ...


class DoubaoProvider(ImageProvider):
    provider_key = "doubao"

    def __init__(self, api_key: str, model: str = "doubao-seedream-5-0-260128",
                 base_url: str = "https://ark.cn-beijing.volces.com/api/v3", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def generate(self, prompt: str, size: str) -> bytes:
        resp = requests.post(
            f"{self._base_url}/images/generations",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "prompt": prompt,
                  "response_format": "url", "size": size,
                  "stream": False, "watermark": False},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"Doubao error ({resp.status_code}): "
                             f"{data.get('error', {}).get('message', str(data))}")
        url = data.get("data", [{}])[0].get("url")
        if not url:
            raise ValueError(f"No image URL: {data}")
        return _download_image(url)


class OpenAIProvider(ImageProvider):
    provider_key = "openai"

    def __init__(self, api_key: str, model: str = "dall-e-3",
                 base_url: str = "https://api.openai.com/v1", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def generate(self, prompt: str, size: str) -> bytes:
        resp = requests.post(
            f"{self._base_url}/images/generations",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "prompt": prompt,
                  "n": 1, "size": size, "response_format": "url"},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"OpenAI error ({resp.status_code}): "
                             f"{data.get('error', {}).get('message', str(data))}")
        url = data.get("data", [{}])[0].get("url")
        if not url:
            raise ValueError(f"No image URL: {data}")
        return _download_image(url)


class GeminiProvider(ImageProvider):
    provider_key = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-image-preview",
                 base_url: str = "https://generativelanguage.googleapis.com/v1beta", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def generate(self, prompt: str, size: str) -> bytes:
        if "x" in size:
            w, h = size.split("x", 1)
            prompt = f"{prompt}\n\nGenerate this image at {w}x{h} resolution."
        resp = requests.post(
            f"{self._base_url}/models/{self._model}:generateContent",
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": self._api_key},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}},
            timeout=120,
        )
        if resp.status_code != 200:
            msg = resp.text[:200]
            try:
                msg = resp.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise ValueError(f"Gemini error ({resp.status_code}): {msg}")
        for part in resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
            inline = part.get("inlineData")
            if inline and inline.get("mimeType", "").startswith("image/"):
                return base64.b64decode(inline["data"])
        raise ValueError("No image in Gemini response")


class DashScopeProvider(ImageProvider):
    provider_key = "dashscope"

    def __init__(self, api_key: str, model: str = "qwen-image-2.0-pro",
                 base_url: str = "https://dashscope.aliyuncs.com/api/v1", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def generate(self, prompt: str, size: str) -> bytes:
        ds_size = size.replace("x", "*")
        resp = requests.post(
            f"{self._base_url}/services/aigc/multimodal-generation/generation",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
                "parameters": {"prompt_extend": False, "size": ds_size, "watermark": False},
            },
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"DashScope error ({resp.status_code}): "
                             f"{data.get('message', str(data))}")
        output = data.get("output", {})
        img = output.get("result_image")
        if not img:
            choices = output.get("choices", [])
            if choices:
                for c in choices[0].get("message", {}).get("content", []):
                    if "image" in c:
                        img = c["image"]
                        break
        if not img:
            raise ValueError(f"No image in DashScope response: {data}")
        if img.startswith("http"):
            return _download_image(img)
        return base64.b64decode(img)


PROVIDERS = {
    "doubao": DoubaoProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "dashscope": DashScopeProvider,
}


def _build_provider_chain(config: dict) -> list[ImageProvider]:
    img_cfg = config.get("image", {})
    providers_list = img_cfg.get("providers")

    if providers_list and isinstance(providers_list, list):
        chain = []
        for entry in providers_list:
            try:
                provider_name = entry.get("provider", "doubao")
                api_key = entry.get("api_key")
                if not api_key:
                    continue
                provider_cls = PROVIDERS.get(provider_name)
                if not provider_cls:
                    continue
                kwargs = {"api_key": api_key}
                if entry.get("model"):
                    kwargs["model"] = entry["model"]
                if entry.get("base_url"):
                    kwargs["base_url"] = entry["base_url"]
                if entry.get("secret_key"):
                    kwargs["secret_key"] = entry["secret_key"]
                if entry.get("deployment"):
                    kwargs["deployment"] = entry["deployment"]
                chain.append(provider_cls(**kwargs))
            except ValueError:
                continue
        if not chain:
            raise ValueError("No valid providers in image.providers list.")
        return chain

    api_key = img_cfg.get("api_key")
    if not api_key:
        raise ValueError("image.api_key not set in config.yaml.")
    provider_name = img_cfg.get("provider", "doubao")
    provider_cls = PROVIDERS.get(provider_name)
    if not provider_cls:
        raise ValueError(f"Unknown provider: '{provider_name}'")
    return [provider_cls(api_key=api_key, model=img_cfg.get("model", None))]


def generate_image(
    prompt: str,
    output_path: str,
    size: str = "cover",
    config: dict = None,
) -> str:
    if config is None:
        config = _load_config()

    chain = _build_provider_chain(config)
    last_error = None

    for provider in chain:
        resolved_size = provider.resolve_size(size)
        try:
            raw_bytes = provider.generate(prompt, resolved_size)
        except Exception as e:
            last_error = e
            continue

        if len(raw_bytes) > MAX_FILE_SIZE:
            from io import BytesIO
            from PIL import Image
            img = Image.open(BytesIO(raw_bytes))
            if img.mode == "RGBA":
                img = img.convert("RGB")
            for quality in (90, 80, 70, 60, 50):
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                if buf.tell() <= MAX_FILE_SIZE:
                    raw_bytes = buf.getvalue()
                    break

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw_bytes)
        return str(output)

    raise ValueError(f"All providers failed. Last error: {last_error}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate images using AI")
    ap.add_argument("--prompt", required=True, help="Image generation prompt")
    ap.add_argument("--output", required=True, help="Output file path")
    ap.add_argument("--size", default="cover", help="Size: cover, article, vertical, square, or WxH")
    ap.add_argument("--provider", default=None, help=f"Override provider")
    args = ap.parse_args()

    try:
        config = _load_config()
        if args.provider:
            config.setdefault("image", {})["provider"] = args.provider
        path = generate_image(args.prompt, args.output, size=args.size, config=config)
        print(f"Image saved: {path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)