# WeWrite 项目工作流程审计报告

**审计日期**: 2026-10-26  
**审计对象**: WeWrite 养生热潮文章发布流程  
**问题总数**: 7 个主要问题类别  
**优先级**: 2 高 / 2 中 / 3 低  

---

## 执行摘要

在测试"养生热潮下的真相"这篇文章的完整发布流程时，发现了**系统性的问题**，而不仅仅是单篇文章的缺陷。这些问题涉及：

- **图片路径处理**: Markdown 中的本地路径未被正确替换
- **网络超时**: 上传大文件时可能超时
- **参数验证**: 图片 API 尺寸参数未自动修正
- **配置管理**: 配置验证不完整
- **数据流转**: 步骤间的数据传递缺乏验证
- **测试覆盖**: 缺少端到端集成测试
- **日志系统**: 调试信息不足

---

## 问题详情

### [高优先级] 问题 1: 图片路径处理机制缺陷

**症状**
```
✗ 发布时 Markdown 中的图片引用没有被 WeChat CDN URL 替换
✗ 导致用户看到的文章中图片引用仍为本地路径（如 yangsheng-1.jpg）
```

**根本原因**

在 `toolkit/cli.py` 的 `cmd_publish()` 函数（第 220-233 行）中：

```python
for img_src in result.images:
    if img_src.startswith(("http://", "https://")):
        continue
    img_path = _resolve_image_path(unquote(img_src), Path(args.input).resolve())
    if img_path.is_file():
        wechat_url = upload_image(token, str(img_path))
        html = html.replace(img_src, wechat_url)  # 👈 只替换 HTML
```

**问题分析**
- 只替换了 `result.html` 中的图片路径
- 原始 Markdown 文件中的本地路径未被处理
- 如果用户导出或检查 Markdown 源文件，会看到不完整的路径

**影响范围**
- 中等：生成的 HTML 正确，但数据不一致
- 如果后续流程依赖 Markdown 的完整性会有问题

**推荐修复**

```python
# 方案 1: 也替换 Markdown 中的图片引用
md_text = Path(args.input).read_text(encoding="utf-8")
for img_src in result.images:
    if not img_src.startswith(("http://", "https://")):
        img_path = _resolve_image_path(unquote(img_src), Path(args.input).resolve())
        if img_path.is_file():
            wechat_url = upload_image(token, str(img_path))
            html = html.replace(img_src, wechat_url)
            md_text = md_text.replace(img_src, wechat_url)  # 👈 也替换 MD

# 方案 2: 建立统一的图片映射表
image_map = {}  # {local_path: wechat_url}
for img_src in result.images:
    # ... 上传逻辑
    image_map[img_src] = wechat_url

# 然后统一应用映射
for src, url in image_map.items():
    html = html.replace(src, url)
    md_text = md_text.replace(src, url)
```

**估计工作量**: 1-2 小时

---

### [高优先级] 问题 3: 网络超时和重试机制不够健壮

**症状**
```
✗ 上传大文件时容易超时
✗ 超时时无法清晰的错误提示
✗ 重试逻辑只在图片生成端，上传端缺乏重试
```

**根本原因**

在 `toolkit/wechat_api.py` 中（第 56-71 行）：

```python
API_TIMEOUT = 30  # 单一的超时设置

def upload_image(access_token: str, image_path: str) -> str:
    with open(path, "rb") as f:
        resp = requests.post(
            "https://api.weixin.qq.com/cgi-bin/media/uploadimg",
            timeout=API_TIMEOUT,  # 👈 30秒可能不够
        )
```

**问题分析**
1. `API_TIMEOUT = 30` 秒对于大文件上传（640KB 封面图）不够
2. 没有区分**连接超时**（CONNECT_TIMEOUT）和**读超时**（READ_TIMEOUT）
3. 上传操作没有重试机制，而生成操作有
4. 微信 API 有时响应慢，30 秒容易触发超时

**影响范围**
- 高：发布失败，用户体验差
- 在网络不稳定时频繁出现

**当前超时设置**
```
CONNECT_TIMEOUT = 10   # 建立连接的超时
READ_TIMEOUT = 120     # 在 image_gen.py 中用于生成
                       # 但在 wechat_api.py 中未使用
```

**推荐修复**

```python
# wechat_api.py
CONNECT_TIMEOUT = 10   # 连接时间
READ_TIMEOUT = 120     # 读取时间（足够上传大文件）

def upload_image(access_token: str, image_path: str, retries: int = 3) -> str:
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
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),  # 👈 使用元组
                )
            data = resp.json()
            if "url" not in data:
                raise ValueError(f"errcode={data.get('errcode')}, errmsg={data.get('errmsg')}")
            return data["url"]
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = 2 ** (attempt + 1)  # 指数退避
                print(f"Upload attempt {attempt + 1} failed: {e}. Retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise last_error

def upload_thumb(access_token: str, image_path: str, retries: int = 3) -> str:
    """类似的重试机制"""
    # ...
```

**估计工作量**: 1-2 小时

---

### [中优先级] 问题 2: 图片生成 API 调用的错误处理不完整

**症状**
```
✗ 尺寸参数验证问题：1920x1080 需要改为 1920x1072
✗ 没有清晰的错误提示和自动修正
```

**根本原因**

在 `toolkit/image_gen.py` 中，z-image-turbo（OpenAI）要求尺寸必须是 16 的倍数：

```
1920x1080:  1080 % 16 = 8  ✗ 错误
1920x1072:  1072 % 16 = 0  ✓ 正确
```

但代码中没有自动修正或充分的错误提示。

**问题分析**
- 当前的 SIZE_PRESETS 设置正确（使用 1920x816）
- 但如果用户直接传入不合法的尺寸，会报错
- 错误信息不够清晰

**推荐修复**

```python
# image_gen.py
def _align_size_to_16(size_str: str) -> str:
    """将尺寸对齐到 16 的倍数"""
    try:
        w, h = map(int, size_str.split('x'))
    except ValueError:
        return size_str
    
    # 向上舍入到 16 的倍数
    aligned_w = ((w + 15) // 16) * 16
    aligned_h = ((h + 15) // 16) * 16
    
    if (w, h) != (aligned_w, aligned_h):
        print(f"[INFO] Size adjusted {w}x{h} → {aligned_w}x{aligned_h} (必须是 16 的倍数)", file=sys.stderr)
    
    return f"{aligned_w}x{aligned_h}"

class OpenAIProvider(ImageProvider):
    def generate(self, prompt: str, size: str) -> bytes:
        size = _align_size_to_16(size)  # 👈 自动修正
        resp = requests.post(...)
        # ...
```

**估计工作量**: 30 分钟

---

### [中优先级] 问题 4: 配置验证和错误提示不够友好

**症状**
```
✗ 配置缺失时错误信息模糊
✗ 没有区分致命错误和可忽略错误
✗ 没有检查配置文件的语法错误
```

**根本原因**

在 `toolkit/cli.py` 中（第 189-204 行）：

```python
cfg = load_config()
appid = args.appid or wechat_cfg.get("appid")
if not appid or not secret:
    print("Error: --appid and --secret required")
```

**问题分析**
1. 只检查了 appid/secret，没检查其他必需字段（author, theme）
2. 配置文件加载失败时没有及时反馈
3. 没有清晰的错误分类

**推荐修复**

```python
# config.py
def validate_config(cfg: dict) -> tuple[bool, list[str]]:
    """验证配置，返回 (是否有效, 错误信息列表)"""
    errors = []
    
    # 必需字段
    required_fields = {
        ("wechat", "appid"): "微信 AppID",
        ("wechat", "secret"): "微信 Secret",
        ("author",): "作者名",
        ("theme",): "默认主题",
    }
    
    for keys, desc in required_fields.items():
        val = cfg
        for key in keys:
            val = val.get(key) if isinstance(val, dict) else None
        if not val:
            errors.append(f"缺失配置 {desc}: {'.'.join(keys)}")
    
    # 检查 theme 是否有效
    if "theme" in cfg and cfg["theme"] not in THEMES:
        errors.append(f"未知的主题: {cfg['theme']}")
    
    return len(errors) == 0, errors

# cli.py
cfg = load_config()
valid, errors = validate_config(cfg)
if not valid:
    for err in errors:
        print(f"配置错误: {err}", file=sys.stderr)
    sys.exit(1)
```

**估计工作量**: 1 小时

---

### [低优先级] 问题 5: 工作流程各步骤间的数据传递缺乏验证

**症状**
```
⚠️  从 Markdown → HTML 转换时，图片引用格式不一致
```

**问题分析**
- Markdown 解析器和 HTML 生成器之间的数据流缺乏检查
- 如果图片引用格式不一致会导致路径替换失败

**推荐修复**

建立中间表示（Intermediate Representation, IR）来追踪数据流：

```python
@dataclass
class ConvertResult:
    title: str
    digest: str
    html: str
    images: list[str]  # 规范化的图片引用列表
    
    def validate(self) -> tuple[bool, list[str]]:
        """验证转换结果的完整性"""
        errors = []
        
        # 检查标题
        if not self.title or len(self.title) > 100:
            errors.append(f"标题无效: '{self.title}'")
        
        # 检查图片引用一致性
        for img in self.images:
            if img.startswith(("http://", "https://")) or Path(img).exists():
                continue
            errors.append(f"图片文件不存在: {img}")
        
        return len(errors) == 0, errors
```

**估计工作量**: 1-2 小时

---

### [低优先级] 问题 6: 缺少完整的端到端测试

**症状**
```
✗ 发布后没有验证数据是否完整抵达微信
✗ 没有测试覆盖常见的边界情况
```

**推荐修复**

创建 `tests/test_e2e.py`：

```python
import pytest
from pathlib import Path
from toolkit.cli import cmd_publish

def test_e2e_publish_article():
    """端到端测试：完整的发布流程"""
    # 1. 生成测试文章
    test_md = Path("tests/fixtures/test-article.md")
    test_cover = Path("tests/fixtures/test-cover.jpg")
    
    # 2. 执行发布
    args = argparse.Namespace(
        input=str(test_md),
        cover=str(test_cover),
        theme="moyu-green",
        appid=os.getenv("TEST_APPID"),
        secret=os.getenv("TEST_SECRET"),
    )
    cmd_publish(args)
    
    # 3. 验证草稿
    # ... 检查 media_id 有效性
    # ... 检查图片是否上传成功
    # ... 检查内容是否完整

@pytest.mark.parametrize("size", ["cover", "article", "vertical", "square"])
def test_size_validation(size):
    """测试图片尺寸参数验证"""
    # ...

def test_timeout_handling():
    """测试超时和重试"""
    # ...

def test_special_characters():
    """测试特殊字符处理（Unicode、表情等）"""
    # ...
```

**估计工作量**: 2-3 小时

---

### [低优先级] 问题 7: 日志记录和调试信息不足

**症状**
```
✗ 大量使用 print()，难以过滤和搜索
✗ 没有日志级别区分
✗ 没有时间戳和上下文
```

**推荐修复**

建立统一的日志系统：

```python
# toolkit/logging_config.py
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(log_file: str = None, level: int = logging.INFO):
    """设置全局日志"""
    logger = logging.getLogger("wewrite")
    
    # 日志格式
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.setLevel(logging.DEBUG)
    return logger

# 在 cli.py 中使用
logger = setup_logging(log_file=f"logs/wewrite-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log")

# 替换所有 print()
logger.info(f"Uploading image: {img_src}")
logger.error(f"Upload failed: {e}")
logger.debug(f"Resolved path: {img_path}")
```

**估计工作量**: 1-2 小时

---

## 修复计划

### 第一阶段（高优先级）- 预计 2-3 小时

1. **问题 1**: 图片路径处理（1-2 小时）
   - 修改 `cli.py` 的 `cmd_publish()`
   - 测试图片替换逻辑
   
2. **问题 3**: 网络超时和重试（1-2 小时）
   - 修改 `wechat_api.py`
   - 添加重试机制
   - 分离 CONNECT_TIMEOUT 和 READ_TIMEOUT

### 第二阶段（中优先级）- 预计 2-3 小时

3. **问题 2**: API 参数验证（30 分钟）
   - 添加 `_align_size_to_16()` 函数
   - 集成到 `OpenAIProvider.generate()`

4. **问题 4**: 配置验证（1 小时）
   - 添加 `validate_config()` 函数
   - 集成到 CLI 初始化

### 第三阶段（低优先级）- 预计 3-4 小时

5. **问题 5**: 数据验证（1-2 小时）
   - 添加 `ConvertResult.validate()` 方法
   - 集成验证检查

6. **问题 6**: E2E 测试（2-3 小时）
   - 创建测试框架
   - 编写集成测试用例

7. **问题 7**: 日志系统（1-2 小时）
   - 创建 `logging_config.py`
   - 替换所有 print() 调用

---

## 今天"养生热潮"文章的具体症状

虽然文章最终发布成功，但暴露了这些问题：

| 问题 | 症状 | 影响 |
|------|------|------|
| 问题 1 | MD 中图片引用未更新 | 中 |
| 问题 2 | 手动调整尺寸参数 | 低 |
| 问题 3 | 上传时心理压力大（怕超时） | 高 |
| 问题 4 | 配置检查不全 | 低 |
| 问题 5 | 数据流转不透明 | 低 |
| 问题 6 | 没有验证最终草稿 | 中 |
| 问题 7 | 调试时信息零散 | 低 |

---

## 测试清单

修复完成后需要进行的测试：

- [ ] 发布文章 → 验证所有图片路径已替换
- [ ] 网络不稳定情况下上传大文件 → 验证重试机制
- [ ] 传入非法尺寸参数 → 验证自动修正
- [ ] 配置文件缺失关键字段 → 验证错误提示
- [ ] 转换结果验证 → 检查数据完整性
- [ ] 端到端发布流程 → 完整的测试覆盖
- [ ] 检查日志输出 → 验证日志系统

---

## 后续建议

1. **自动化检查**: 在每次发布前运行验证脚本
2. **预发布检验**: 验证草稿内容后再提示发布
3. **版本管理**: 对配置文件进行版本控制
4. **监控告警**: 记录发布过程中的错误
5. **文档完善**: 补充故障排查文档

---

**报告签署**

生成时间: 2026-10-26 06:25:00  
审计方式: 自动化代码审计 + 手动工作流程分析  
建议状态: 待采纳  

