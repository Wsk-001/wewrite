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


def _load_config() -> dict:
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent))
        from config import load_config
        return load_config()
    except ImportError:
        for p in [
            Path(__file__).parent.parent / "config" / "config.yaml",
            Path(__file__).parent.parent / "config.yaml",
            Path(__file__).parent / "config.yaml",
            Path.home() / ".config" / "wewrite" / "config.yaml",
        ]:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        return {}


# 封面用微信首图比例 2.35:1，各 provider 只差分辨率，不要改动比例。
# 若改用官方 OpenAI dall-e-3（只支持 1024x1024 / 1792x1024 / 1024x1792），
# 请显式传 --size 1792x1024，不要用 cover 预设。
SIZE_PRESETS = {
    "cover": {
        "doubao": "2952x1256", "openai": "1920x816", "gemini": "1920x816",
        "dashscope": "1920x816", "minimax": "1920x816", "replicate": "1920x816",
        "azure_openai": "1920x816", "openrouter": "1920x816", "jimeng": "1920x816",
    },
    "article": {
        "doubao": "2560x1440", "openai": "1792x1024", "gemini": "1792x1024",
        "dashscope": "1792x1024", "minimax": "1792x1024", "replicate": "1792x1024",
        "azure_openai": "1792x1024", "openrouter": "1792x1024", "jimeng": "1792x1024",
    },
    "vertical": {
        "doubao": "1088x2560", "openai": "1024x1792", "gemini": "1024x1792",
        "dashscope": "1024x1792", "minimax": "1024x1792", "replicate": "1024x1792",
        "azure_openai": "1024x1792", "openrouter": "1024x1792", "jimeng": "1024x1792",
    },
    "square": {
        "doubao": "2048x2048", "openai": "1024x1024", "gemini": "1024x1024",
        "dashscope": "1024x1024", "minimax": "1024x1024", "replicate": "1024x1024",
        "azure_openai": "1024x1024", "openrouter": "1024x1024", "jimeng": "1024x1024",
    },
}

MAX_FILE_SIZE = 5 * 1024 * 1024


class ImageProvider(abc.ABC):
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
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "prompt": prompt, "response_format": "url", "size": size, "stream": False, "watermark": False},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"Doubao error ({resp.status_code}): {data.get('error', {}).get('message', str(data))}")
        url = data.get("data", [{}])[0].get("url")
        if not url:
            raise ValueError(f"No image URL: {data}")
        return requests.get(url, timeout=60).content


class OpenAIProvider(ImageProvider):
    provider_key = "openai"
    def __init__(self, api_key: str, model: str = "dall-e-3",
                 base_url: str = "https://api.openai.com/v1", size_param: str = "size", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._size_param = size_param
    def generate(self, prompt: str, size: str) -> bytes:
        body = {"model": self._model, "prompt": prompt, "n": 1, "response_format": "url"}
        if self._size_param == "width_height":
            # 部分聚合网关（如 moark 的 z-image-turbo）只认 width/height 两个字段，
            # 传单个 "1792x1024" 字符串会被静默忽略并返回方图。
            try:
                w, h = (int(x) for x in size.lower().split("x", 1))
            except ValueError:
                raise ValueError(f"size_param=width_height 需要 WxH 格式，收到: {size}")
            body["width"] = w
            body["height"] = h
        else:
            body[self._size_param] = size
        resp = requests.post(
            f"{self._base_url}/images/generations",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
            json=body,
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"OpenAI error ({resp.status_code}): {data.get('error', {}).get('message', str(data))}")
        item = data.get("data", [{}])[0]
        url = item.get("url")
        if url:
            return requests.get(url, timeout=60).content
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        raise ValueError(f"No image URL: {data}")


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
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
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
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
                  "parameters": {"prompt_extend": False, "size": ds_size, "watermark": False}},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"DashScope error ({resp.status_code}): {data.get('message', str(data))}")
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
            return requests.get(img, timeout=60).content
        return base64.b64decode(img)


class MiniMaxProvider(ImageProvider):
    provider_key = "minimax"
    def __init__(self, api_key: str, model: str = "image-01",
                 base_url: str = "https://api.minimax.io/v1", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
    def generate(self, prompt: str, size: str) -> bytes:
        w, h = 1024, 1024
        try:
            w, h = (int(x) for x in size.split("x", 1))
        except ValueError:
            pass
        resp = requests.post(
            f"{self._base_url}/image_generation",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "prompt": prompt, "response_format": "base64", "width": w, "height": h, "n": 1},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"MiniMax error ({resp.status_code}): {data}")
        b64_list = data.get("data", {}).get("image_base64", [])
        if not b64_list:
            raise ValueError(f"No image in MiniMax response: {data}")
        return base64.b64decode(b64_list[0])


class ReplicateProvider(ImageProvider):
    provider_key = "replicate"
    _POLL_INTERVAL = 2
    _POLL_TIMEOUT = 300
    def __init__(self, api_key: str, model: str = "google/nano-banana-pro",
                 base_url: str = "https://api.replicate.com/v1", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
    def generate(self, prompt: str, size: str) -> bytes:
        aspect = "16:9"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}", "Prefer": "wait=60"}
        resp = requests.post(
            f"{self._base_url}/models/{self._model}/predictions",
            headers=headers,
            json={"input": {"prompt": prompt, "aspect_ratio": aspect, "number_of_images": 1, "output_format": "png"}},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code not in (200, 201):
            raise ValueError(f"Replicate error ({resp.status_code}): {data}")
        poll_url = data.get("urls", {}).get("get")
        deadline = time.monotonic() + self._POLL_TIMEOUT
        while data.get("status") not in ("succeeded", "failed", "canceled"):
            if time.monotonic() > deadline:
                raise ValueError("Replicate polling timeout")
            time.sleep(self._POLL_INTERVAL)
            data = requests.get(poll_url, headers=headers, timeout=30).json()
        if data.get("status") != "succeeded":
            raise ValueError(f"Replicate failed: {data.get('error')}")
        output = data.get("output")
        if isinstance(output, list):
            output = output[0]
        if isinstance(output, dict):
            output = output.get("url", output.get("uri"))
        if not output or not isinstance(output, str):
            raise ValueError(f"No image URL in Replicate output: {data}")
        return requests.get(output, timeout=60).content


class AzureOpenAIProvider(ImageProvider):
    provider_key = "azure_openai"
    def __init__(self, api_key: str, model: str = "dall-e-3",
                 base_url: str = "", deployment: str = "", **_kw):
        self._api_key = api_key
        self._deployment = deployment or model
        self._base_url = base_url.rstrip("/")
    def generate(self, prompt: str, size: str) -> bytes:
        if not self._base_url:
            raise ValueError("Azure OpenAI requires base_url")
        resp = requests.post(
            f"{self._base_url}/deployments/{self._deployment}/images/generations?api-version=2025-04-01-preview",
            headers={"Content-Type": "application/json", "api-key": self._api_key},
            json={"prompt": prompt, "size": size, "n": 1, "quality": "medium"},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"Azure OpenAI error ({resp.status_code}): {data}")
        item = data.get("data", [{}])[0]
        if item.get("url"):
            return requests.get(item["url"], timeout=60).content
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        raise ValueError(f"No image in Azure response: {data}")


class OpenRouterProvider(ImageProvider):
    provider_key = "openrouter"
    def __init__(self, api_key: str, model: str = "google/gemini-3.1-flash-image-preview",
                 base_url: str = "https://openrouter.ai/api/v1", **_kw):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
    def generate(self, prompt: str, size: str) -> bytes:
        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "messages": [{"role": "user", "content": prompt}],
                  "modalities": ["image"], "stream": False},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"OpenRouter error ({resp.status_code}): {data}")
        choice = data.get("choices", [{}])[0].get("message", {})
        images = choice.get("images", [])
        if images:
            img = images[0]
            if img.startswith("http"):
                return requests.get(img, timeout=60).content
            if img.startswith("data:"):
                _, b64 = img.split(",", 1)
                return base64.b64decode(b64)
        content = choice.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image":
                    url = item.get("url") or item.get("image_url", {}).get("url")
                    if url:
                        if url.startswith("data:"):
                            _, b64 = url.split(",", 1)
                            return base64.b64decode(b64)
                        return requests.get(url, timeout=60).content
        raise ValueError(f"No image in OpenRouter response: {data}")


class JimengProvider(ImageProvider):
    provider_key = "jimeng"
    _POLL_INTERVAL = 2
    _POLL_MAX_ATTEMPTS = 60
    def __init__(self, api_key: str, secret_key: str = "",
                 model: str = "jimeng_t2i_v40",
                 base_url: str = "https://visual.volcengineapi.com", **_kw):
        self._access_key = api_key
        self._secret_key = secret_key
        self._model = model
        self._base_url = base_url
    def _sign(self, method, path, query, headers, payload):
        now = datetime.now(timezone.utc)
        date_stamp = now.strftime("%Y%m%d")
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        signed_headers_list = sorted(k.lower() for k in headers)
        signed_headers_str = ";".join(signed_headers_list)
        canonical = "\n".join([method, path, query,
            "".join(f"{k.lower()}:{headers[k]}\n" for k in sorted(headers)),
            signed_headers_str,
            hashlib.sha256(payload).hexdigest()])
        region, service, scope = "cn-north-1", "cv", f"{date_stamp}/cn-north-1/cv/request"
        string_to_sign = "\n".join(["HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
        def _hmac(key, msg):
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()
        k_date = _hmac(self._secret_key.encode(), date_stamp)
        k_region = _hmac(k_date, region)
        k_service = _hmac(k_region, service)
        k_signing = _hmac(k_service, "request")
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
        auth = f"HMAC-SHA256 Credential={self._access_key}/{scope}, SignedHeaders={signed_headers_str}, Signature={signature}"
        return {**headers, "Authorization": auth, "X-Date": amz_date}
    def _request(self, action, body):
        payload = json.dumps(body).encode()
        path, query = "/", f"Action={action}&Version=2022-08-31"
        headers = {"Content-Type": "application/json", "Host": self._base_url.replace("https://", "").replace("http://", "")}
        signed = self._sign("POST", path, query, headers, payload)
        resp = requests.post(f"{self._base_url}/?{query}", headers=signed, data=payload, timeout=120)
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"Jimeng error ({resp.status_code}): {data}")
        return data
    def generate(self, prompt: str, size: str) -> bytes:
        if not self._secret_key:
            raise ValueError("Jimeng requires secret_key")
        w, h = 1024, 1024
        try:
            w, h = (int(x) for x in size.split("x", 1))
        except ValueError:
            pass
        submit = self._request("CVSync2AsyncSubmitTask", {"req_key": self._model, "prompt": prompt, "width": w, "height": h})
        task_id = submit.get("data", {}).get("task_id")
        if not task_id:
            raise ValueError(f"No task_id from Jimeng: {submit}")
        for _ in range(self._POLL_MAX_ATTEMPTS):
            time.sleep(self._POLL_INTERVAL)
            result = self._request("CVSync2AsyncGetResult", {"req_key": self._model, "task_id": task_id})
            code = result.get("code")
            if code == 10000:
                data = result.get("data", {})
                b64_list = data.get("binary_data_base64", [])
                if b64_list:
                    return base64.b64decode(b64_list[0])
                urls = data.get("image_urls", [])
                if urls:
                    return requests.get(urls[0], timeout=60).content
                raise ValueError(f"No image data in Jimeng result: {result}")
            if code and code != 10000:
                status = result.get("data", {}).get("status")
                if status in ("failed", "canceled"):
                    raise ValueError(f"Jimeng task failed: {result}")
        raise ValueError("Jimeng polling timeout")


PROVIDERS = {
    "doubao": DoubaoProvider, "openai": OpenAIProvider, "gemini": GeminiProvider,
    "dashscope": DashScopeProvider, "minimax": MiniMaxProvider, "replicate": ReplicateProvider,
    "azure_openai": AzureOpenAIProvider, "openrouter": OpenRouterProvider, "jimeng": JimengProvider,
}


def _build_provider_chain(config: dict) -> list:
    img_cfg = config.get("image", {})
    providers_list = img_cfg.get("providers")
    if providers_list and isinstance(providers_list, list):
        chain = []
        for entry in providers_list:
            provider_name = entry.get("provider", "doubao")
            api_key = entry.get("api_key")
            if not api_key:
                continue
            cls = PROVIDERS.get(provider_name)
            if not cls:
                continue
            kwargs = {"api_key": api_key}
            if entry.get("model"):
                kwargs["model"] = entry["model"]
            if entry.get("base_url"):
                kwargs["base_url"] = entry["base_url"]
            if entry.get("size_param"):
                kwargs["size_param"] = entry["size_param"]
            if entry.get("secret_key"):
                kwargs["secret_key"] = entry["secret_key"]
            if entry.get("deployment"):
                kwargs["deployment"] = entry["deployment"]
            chain.append(cls(**kwargs))
        if not chain:
            raise ValueError("No valid providers in image.providers list")
        return chain
    api_key = img_cfg.get("api_key")
    if not api_key:
        raise ValueError("image.api_key not set in config.yaml")
    cls = PROVIDERS.get(img_cfg.get("provider", "doubao"), DoubaoProvider)
    return [cls(api_key=api_key, model=img_cfg.get("model", ""), base_url=img_cfg.get("base_url", ""))]


def _center_crop_to_ratio(raw_bytes: bytes, size: str) -> bytes:
    from io import BytesIO
    from PIL import Image

    try:
        w, h = (int(x) for x in size.lower().split("x", 1))
    except ValueError:
        return raw_bytes
    if w <= 0 or h <= 0:
        return raw_bytes

    img = Image.open(BytesIO(raw_bytes))
    target_ratio = w / h
    cur_w, cur_h = img.size
    if abs(cur_w / cur_h - target_ratio) < 0.01:
        return raw_bytes

    if cur_w / cur_h > target_ratio:
        new_w = max(1, int(cur_h * target_ratio))
        left = (cur_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, cur_h))
    else:
        new_h = max(1, int(cur_w / target_ratio))
        top = (cur_h - new_h) // 2
        img = img.crop((0, top, cur_w, top + new_h))

    buf = BytesIO()
    fmt = "PNG" if img.mode == "RGBA" else "JPEG"
    if fmt == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    img.save(buf, format=fmt, quality=90)
    return buf.getvalue()


def _warn_size_mismatch(raw_bytes: bytes, size: str, provider_key: str) -> None:
    """provider 静默忽略尺寸参数时，裁切会切掉构图。这里显式告警，避免无声产出残图。"""
    from io import BytesIO
    from PIL import Image

    try:
        w, h = (int(x) for x in size.lower().split("x", 1))
        got = Image.open(BytesIO(raw_bytes)).size
    except Exception:
        return
    requested_ratio = w / h
    actual_ratio = got[0] / got[1]
    if abs(actual_ratio - requested_ratio) / requested_ratio > 0.02:
        print(
            f"[警告] provider '{provider_key}' 返回 {got[0]}x{got[1]}，"
            f"与请求 {w}x{h} 的比例不一致；已中心裁切，构图可能被切边。"
            f"请检查 size_param 是否被该接口支持（部分网关需 width/height 双字段）。",
            file=sys.stderr,
        )


def _ensure_output_format(raw_bytes: bytes, output_path: str) -> bytes:
    """让落盘字节与文件扩展名一致。

    provider 常返回 PNG；比例正好匹配时裁切函数会原样返回，于是 PNG 字节被写进
    .jpg 文件，导致扩展名、实际内容、上传时的 MIME 三者不一致（微信侧靠嗅探能
    勉强显示，但部分平台会直接拒收）。
    """
    from io import BytesIO
    from PIL import Image

    ext = Path(output_path).suffix.lower()
    want = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}.get(ext)
    if not want:
        return raw_bytes
    img = Image.open(BytesIO(raw_bytes))
    if img.format == want or (want == "JPEG" and img.format in ("JPEG", "MPO")):
        return raw_bytes
    if want == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format=want, **({"quality": 92, "optimize": True} if want == "JPEG" else {}))
    return buf.getvalue()


def generate_image(prompt: str, output_path: str, size: str = "cover", config: dict = None) -> str:
    if config is None:
        config = _load_config()
    chain = _build_provider_chain(config)
    last_error = None
    for provider in chain:
        resolved_size = provider.resolve_size(size)
        raw_bytes = None
        for attempt in range(3):
            try:
                raw_bytes = provider.generate(prompt, resolved_size)
                break
            except Exception as e:
                last_error = e
                print(f"Provider '{provider.provider_key}' failed: {e}. Trying next...", file=sys.stderr)
                break
        if raw_bytes is None:
            continue
        _warn_size_mismatch(raw_bytes, resolved_size, provider.provider_key)
        raw_bytes = _center_crop_to_ratio(raw_bytes, resolved_size)
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
        raw_bytes = _ensure_output_format(raw_bytes, output_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw_bytes)
        return str(output)
    raise ValueError(f"All providers failed. Last error: {last_error}")


def main():
    ap = argparse.ArgumentParser(description="Generate images using AI")
    ap.add_argument("--prompt", required=True, help="Image generation prompt")
    ap.add_argument("--output", required=True, help="Output file path")
    ap.add_argument("--size", default="cover", help="Size: cover, article, vertical, square, or WxH")
    ap.add_argument("--provider", default=None, help=f"Override provider ({', '.join(PROVIDERS)})")
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


if __name__ == "__main__":
    main()
