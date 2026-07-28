import json
import requests
from dataclasses import dataclass
from typing import Optional


@dataclass
class DraftResult:
    media_id: str


@dataclass
class ImagePostResult:
    media_id: str
    image_count: int


def create_draft(
    access_token: str,
    title: str,
    html: str,
    digest: str,
    thumb_media_id: Optional[str] = None,
    author: Optional[str] = None,
) -> DraftResult:
    article = {
        "title": title,
        "author": author or "",
        "digest": digest,
        "content": html,
        "show_cover_pic": 0,
    }
    if thumb_media_id:
        article["thumb_media_id"] = thumb_media_id
    body = {"articles": [article]}
    resp = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/add",
        params={"access_token": access_token},
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    data = resp.json()
    errcode = data.get("errcode", 0)
    if errcode != 0:
        errmsg = data.get("errmsg", "unknown error")
        raise ValueError(f"WeChat create_draft error: errcode={errcode}, errmsg={errmsg}")
    if "media_id" not in data:
        raise ValueError(f"WeChat create_draft error: missing media_id in response: {data}")
    return DraftResult(media_id=data["media_id"])


def get_draft(access_token: str, media_id: str) -> str:
    resp = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/get",
        params={"access_token": access_token},
        json={"media_id": media_id},
    )
    resp.encoding = "utf-8"
    data = resp.json()
    errcode = data.get("errcode", 0)
    if errcode != 0:
        errmsg = data.get("errmsg", "unknown error")
        raise ValueError(f"WeChat get_draft error: errcode={errcode}, errmsg={errmsg}")
    articles = data.get("news_item", [])
    if not articles:
        raise ValueError(f"WeChat get_draft: no articles in draft {media_id}")
    return articles[0].get("content", "")


def html_to_plaintext(html: str) -> str:
    import re
    import html as html_module
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<(br|p|div|section|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def create_image_post(
    access_token: str,
    title: str,
    image_media_ids: list[str],
    content: str = "",
    open_comment: bool = False,
    fans_only_comment: bool = False,
) -> ImagePostResult:
    if not image_media_ids:
        raise ValueError("At least 1 image is required for image post")
    if len(image_media_ids) > 20:
        raise ValueError(f"Max 20 images allowed, got {len(image_media_ids)}")
    if len(title) > 32:
        raise ValueError(f"Title max 32 chars for image post, got {len(title)}")
    article = {
        "article_type": "newspic",
        "title": title,
        "content": content,
        "image_info": {"image_list": [{"image_media_id": mid} for mid in image_media_ids]},
        "need_open_comment": 1 if open_comment else 0,
        "only_fans_can_comment": 1 if fans_only_comment else 0,
    }
    body = {"articles": [article]}
    resp = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/add",
        params={"access_token": access_token},
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    data = resp.json()
    errcode = data.get("errcode", 0)
    if errcode != 0:
        errmsg = data.get("errmsg", "unknown error")
        raise ValueError(f"WeChat create_image_post error: errcode={errcode}, errmsg={errmsg}")
    if "media_id" not in data:
        raise ValueError(f"WeChat create_image_post: missing media_id in response: {data}")
    return ImagePostResult(media_id=data["media_id"], image_count=len(image_media_ids))
