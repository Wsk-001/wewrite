#!/usr/bin/env python3
"""按 media_id 删除微信草稿箱草稿。

用法：
    python3 scripts/delete_drafts.py <media_id> [media_id ...]

流程约定（见 output/history.yaml 头部说明）：
    删除前先调 draft/batchget 核对实时状态，用户确认后再执行本脚本，
    删除后立即更新 history.yaml 对应 action。
"""

import sys
import json
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
from config_manager import load_config
from wechat_api import ensure_valid_token


def delete_draft(access_token: str, media_id: str) -> bool:
    """Delete a draft by media_id."""
    url = f"https://api.weixin.qq.com/cgi-bin/draft/delete?access_token={access_token}"
    payload = {"media_id": media_id}

    response = requests.post(url, json=payload, timeout=30)
    result = json.loads(response.content.decode("utf-8"))

    if result.get("errcode") == 0:
        print(f"Deleted: {media_id}")
        return True
    print(f"Failed to delete {media_id}: {result.get('errmsg', 'Unknown error')}")
    return False


def main() -> None:
    media_ids = sys.argv[1:]
    if not media_ids:
        print(__doc__)
        sys.exit(2)

    config = load_config()
    wechat_config = config.get("wechat", {})
    appid = wechat_config.get("appid", "")
    secret = wechat_config.get("secret", "")

    if not appid or not secret:
        print("Error: WeChat appid/secret not configured")
        sys.exit(1)

    print(f"Deleting {len(media_ids)} drafts...")
    access_token = ensure_valid_token(appid, secret)

    success_count = 0
    for media_id in media_ids:
        if delete_draft(access_token, media_id):
            success_count += 1

    print(f"\nDeleted {success_count}/{len(media_ids)} drafts")
    sys.exit(0 if success_count == len(media_ids) else 1)


if __name__ == "__main__":
    main()
