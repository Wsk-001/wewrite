# WeWrite 快速修复行动计划

**优先级**: 修复高危问题 + 防护机制  
**目标**: 确保下一篇文章发布时更稳定

---

## 快速修复（24 小时内）

### 修复 1: 图片路径处理 (HIGH)

**文件**: `toolkit/cli.py`  
**行号**: 220-233  
**修改**:

```python
# 原代码
for img_src in result.images:
    if img_src.startswith(("http://", "https://")):
        continue
    img_path = _resolve_image_path(unquote(img_src), Path(args.input).resolve())
    if img_path.is_file():
        print(f"Uploading image: {img_src}")
        wechat_url = upload_image(token, str(img_path))
        html = html.replace(img_src, wechat_url)
        print(f"  -> {wechat_url}")
    else:
        print(f"Warning: image not found: {img_src}")

# 新代码
image_replacements = {}  # {local_path: wechat_url}
for img_src in result.images:
    if img_src.startswith(("http://", "https://")):
        continue
    img_path = _resolve_image_path(unquote(img_src), Path(args.input).resolve())
    if img_path.is_file():
        print(f"Uploading image: {img_src}")
        wechat_url = upload_image(token, str(img_path))
        image_replacements[img_src] = wechat_url
        print(f"  -> {wechat_url}")
    else:
        print(f"Warning: image not found: {img_src}")

# 应用所有替换（HTML + Markdown）
for local_src, wechat_url in image_replacements.items():
    html = html.replace(local_src, wechat_url)
    # 如果需要，也可以更新 MD 文件
    # md_text = md_text.replace(local_src, wechat_url)
```

**测试命令**:
```bash
cd /workspace
python toolkit/cli.py publish output/养生热潮的三大误区.md \
  --cover output/cover-yangsheng.jpg \
  --theme moyu-green

# 验证：检查生成的 HTML 中是否有 mmbiz.qpic.cn URL
```

---

### 修复 2: 网络超时和重试 (HIGH)

**文件**: `toolkit/wechat_api.py`  
**行号**: 1-89  
**修改**:

```python
import time
import mimetypes
import requests
from pathlib import Path
from dataclasses import dataclass

_token_cache: dict = 
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 120  # 👈 新增：足够上传大文件

@dataclass
class TokenResult:
    access_token: str
    expires_at: float
    appid: str
    secret: str

def get_access_token(appid: str, secret: str, force_refresh: bool = False) -> str:
    # ... 保持不变

def upload_image(access_token: str, image_path: str, retries: int = 2) -> str:
    """上传图片，支持重试"""
    last_error = None
    for attempt in range(retries + 1):
        try:
            path = Path(image_path)
            content_type = _guess_content_type(image_path)
            with open(path, "rb") as f:
                resp = requests.post(
                    "https://api.weixin.qq.com/cgi-bin/media/uploadimg",
                    params={"access_token": access_token},
                    files={"media": (path.name, f, content_type)},
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),  # 👈 改为元组
                )
            data = resp.json()
            if "url" not in data:
                errcode = data.get("errcode", "unknown")
                errmsg = data.get("errmsg", "unknown error")
                raise ValueError(f"WeChat upload_image error: errcode={errcode}, errmsg={errmsg}")
            return data["url"]
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = 2 * (attempt + 1)
                print(f"Image upload attempt {attempt + 1} failed: {e}", file=sys.stderr)
                print(f"Retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise last_error

def upload_thumb(access_token: str, image_path: str, retries: int = 2) -> str:
    """上传缩略图，支持重试"""
    last_error = None
    for attempt in range(retries + 1):
        try:
            path = Path(image_path)
            content_type = _guess_content_type(image_path)
            with open(path, "rb") as f:
                resp = requests.post(
                    "https://api.weixin.qq.com/cgi-bin/material/add_material",
                    params={"access_token": access_token, "type": "image"},
                    files={"media": (path.name, f, content_type)},
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),  # 👈 改为元组
                )
            data = resp.json()
            if "media_id" not in data:
                errcode = data.get("errcode", "unknown")
                errmsg = data.get("errmsg", "unknown error")
                raise ValueError(f"WeChat upload_thumb error: errcode={errcode}, errmsg={errmsg}")
            return data["media_id"]
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = 2 * (attempt + 1)
                print(f"Thumbnail upload attempt {attempt + 1} failed: {e}", file=sys.stderr)
                print(f"Retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise last_error
```

**测试命令**:
```bash
# 模拟网络抖动（需要 mock），验证重试逻辑
cd /workspace
python -m pytest tests/test_wechat_api.py -v -k "retry"
```

---

### 修复 3: API 参数验证 (MEDIUM)

**文件**: `toolkit/image_gen.py`  
**行号**: 68-81  
**修改**:

```python
def _align_size_to_16(size_str: str) -> str:
    """将图片尺寸对齐到 16 的倍数（OpenAI/z-image-turbo 的要求）"""
    import sys
    try:
        w, h = map(int, size_str.split('x'))
    except (ValueError, AttributeError):
        return size_str
    
    # 向上舍入到 16 的倍数
    aligned_w = ((w + 15) // 16) * 16
    aligned_h = ((h + 15) // 16) * 16
    
    if (w, h) != (aligned_w, aligned_h):
        print(f"[INFO] Size auto-adjusted: {w}x{h} → {aligned_w}x{aligned_h}", file=sys.stderr)
    
    return f"{aligned_w}x{aligned_h}"

class OpenAIProvider(ImageProvider):
    provider_key = "openai"
    
    def __init__(self, api_key: str, model: str = "dall-e-3", **_kw):
        self._api_key = api_key
        self._model = model
    
    def generate(self, prompt: str, size: str) -> bytes:
        size = _align_size_to_16(size)  # 👈 自动修正
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json={"model": self._model, "prompt": prompt, "size": size, "n": 1, "response_format": "b64_json"},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        # ... 保持其他逻辑不变
```

---

### 修复 4: 配置验证 (MEDIUM)

**文件**: `toolkit/config.py`  
**新增**:

```python
import sys
from typing import Tuple, List

def get_nested(obj: dict, path: str, default=None):
    """获取嵌套字典值，例如 get_nested(cfg, "wechat.appid")"""
    keys = path.split(".")
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return default
    return obj or default

def validate_config(cfg: dict) -> Tuple[bool, List[str]]:
    """验证配置完整性"""
    errors = []
    
    required_fields = {
        "wechat.appid": "微信 AppID",
        "wechat.secret": "微信 Secret",
        "author": "作者名",
        "theme": "默认主题",
    }
    
    for field_path, desc in required_fields.items():
        val = get_nested(cfg, field_path)
        if not val or not str(val).strip():
            errors.append(f"缺失配置: {desc} ({field_path})")
    
    # 验证主题是否存在
    from theme_configs import THEMES
    theme = get_nested(cfg, "theme")
    if theme and theme not in THEMES:
        errors.append(f"未知的主题: {theme}（可用: {', '.join(THEMES.keys())}）")
    
    return len(errors) == 0, errors

# 在 cli.py 中添加验证
def cmd_publish(args):
    _validate_publish_inputs(args)
    
    cfg = load_config()
    valid, errors = validate_config(cfg)  # 👈 新增验证
    if not valid:
        for err in errors:
            print(f"配置错误: {err}", file=sys.stderr)
        sys.exit(1)
    
    # ... 保持其他逻辑
```

---

## 验证脚本

创建 `scripts/verify_publish.py` 来验证发布流程：

```python
#!/usr/bin/env python3
"""发布前验证脚本"""

import sys
import json
from pathlib import Path

def verify_article(md_path: str, cover_path: str) -> bool:
    """验证文章和配图的完整性"""
    print("=" * 70)
    print("发布前验证")
    print("=" * 70)
    
    # 1. 检查文件存在
    print("\n[1] 文件完整性检查")
    md = Path(md_path)
    cover = Path(cover_path)
    
    if not md.exists():
        print(f"  ✗ 文章文件不存在: {md_path}")
        return False
    print(f"  ✓ 文章文件: {md.stat().st_size / 1024:.1f} KB")
    
    if not cover.exists():
        print(f"  ✗ 封面文件不存在: {cover_path}")
        return False
    print(f"  ✓ 封面文件: {cover.stat().st_size / 1024:.1f} KB")
    
    # 2. 检查配图引用
    print("\n[2] 配图完整性检查")
    import re
    content = md.read_text(encoding="utf-8")
    img_refs = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", content)
    
    missing = []
    for alt, src in img_refs:
        if not src.startswith(("http://", "https://")):
            img_path = md.parent / src
            if not img_path.exists():
                print(f"  ✗ 配图不存在: {src}")
                missing.append(src)
            else:
                print(f"  ✓ 配图存在: {src} ({img_path.stat().st_size / 1024:.1f} KB)")
    
    if missing:
        return False
    
    # 3. 检查内容
    print("\n[3] 内容检查")
    lines = content.split("\n")
    word_count = len("".join(lines))
    print(f"  ✓ 文章字数: {word_count}")
    print(f"  ✓ 文章行数: {len(lines)}")
    
    # 4. 检查配置
    print("\n[4] 配置检查")
    from toolkit.config import load_config, validate_config
    cfg = load_config()
    valid, errors = validate_config(cfg)
    if not valid:
        for err in errors:
            print(f"  ✗ {err}")
        return False
    print(f"  ✓ 配置有效")
    
    print("\n" + "=" * 70)
    print("✓ 所有检查通过，可以发布！")
    print("=" * 70)
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python verify_publish.py <文章.md> <封面.jpg>")
        sys.exit(1)
    
    if not verify_article(sys.argv[1], sys.argv[2]):
        sys.exit(1)
```

**运行**:
```bash
python scripts/verify_publish.py output/养生热潮的三大误区.md output/cover-yangsheng.jpg
```

---

## 修复检查清单

- [ ] 修复 1: 图片路径处理（cli.py）
- [ ] 修复 2: 超时和重试（wechat_api.py）
- [ ] 修复 3: API 参数验证（image_gen.py）
- [ ] 修复 4: 配置验证（config.py + cli.py）
- [ ] 创建验证脚本（scripts/verify_publish.py）
- [ ] 运行验证脚本测试
- [ ] 提交更改到 git
- [ ] 用新文章进行 E2E 测试

---

## 测试用例

**测试 1: 正常发布流程**
```bash
python toolkit/cli.py publish tests/fixtures/test-article.md \
  --cover tests/fixtures/test-cover.jpg \
  --theme moyu-green
```

**测试 2: 参数验证**
```bash
# 应该自动修正尺寸
python -c "from toolkit.image_gen import _align_size_to_16; print(_align_size_to_16('1920x1080'))"
# 输出: 1920x1072
```

**测试 3: 配置验证**
```bash
python -c "
from toolkit.config import load_config, validate_config
cfg = load_config()
valid, errors = validate_config(cfg)
print(f'有效: {valid}')
if errors:
    for e in errors: print(f'  - {e}')
"
```

---

**预计完成时间**: 2-3 小时  
**建议在下一篇文章发布前完成**

