"""
视频号(微信频道)分享链接解析：分享链接 → 腾讯元宝换取 exportId/token → 微信频道换取 videoUrl。

移植自 wx_channels_download/internal/api/sph/worker.js，
逻辑与 taixing-ideabox server/skills/prepare_video.py 的 _parse_wechat_yuanbao 一致。
仅用标准库 urllib，无第三方依赖。

依赖环境变量 HY_TOKEN（腾讯元宝 cookie，可在浏览器登录元宝后 F12 获取）。
"""
import json
import os
import random
import time
import urllib.parse
import urllib.request

_SPH_PARSE_URL = "https://yuanbao.tencent.com/api/weixin/get_parse_result"
_SPH_FEED_URL = "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
_SPH_PAGE_URL = "https%3A%2F%2Fchannels.weixin.qq.com%2Ffinder-preview%2Fpages%2Ffeed"
_SPH_REFERER = "https://yuanbao.tencent.com/chat/naQivTmsDa/cf4d0079-ed1b-4c55-a3f3-2ca1379727d1"
_SPH_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


def _sph_rid() -> str:
    ts = f"{int(time.time()):x}"
    rand = "".join(random.choice("0123456789abcdef") for _ in range(8))
    return f"{ts}-{rand}"


def _request_json(url: str, method: str = "GET", payload=None, headers=None, timeout: int = 15) -> dict:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _sph_parse_share_url(share_url: str, cookie: str) -> dict:
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://yuanbao.tencent.com",
        "referer": _SPH_REFERER,
        "user-agent": _SPH_UA,
        "t-userid": "b9575f6b0a8c4a55a08096904a5ef20a",
        "x-agentid": "naQivTmsDa/cf4d0079-ed1b-4c55-a3f3-2ca1379727d1",
        "x-device-id": "1921b001708100d7fa31002b9646bd0cc15a3e2e1f",
        "x-hy92": "e963067ffa31002b9646bd0c03000008b1951a",
        "x-hy93": "1921b001708100d7fa31002b9646bd0cc15a3e2e1f",
        "x-id": "b9575f6b0a8c4a55a08096904a5ef20a",
        "x-platform": "mac",
        "x-source": "web",
        "x-webversion": "2.69.0",
        "cookie": cookie,
    }
    payload = {"type": "video_channel_url", "url": share_url, "scene": 1}
    return _request_json(_SPH_PARSE_URL, method="POST", payload=payload, headers=headers, timeout=15)


def _sph_get_feed_info(export_id: str, general_token: str) -> dict:
    rid = _sph_rid()
    referer = (
        "https://channels.weixin.qq.com/finder-preview/pages/feed"
        f"?entry_card_type=48&comment_scene=39&appid=0&token={general_token}"
        f"&entry_scene=0&eid={export_id}"
    )
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://channels.weixin.qq.com",
        "referer": referer,
        "user-agent": _SPH_UA,
    }
    api_url = f"{_SPH_FEED_URL}?_rid={rid}&_pageUrl={_SPH_PAGE_URL}"
    payload = {"baseReq": {"generalToken": general_token}, "exportId": export_id}
    return _request_json(api_url, method="POST", payload=payload, headers=headers, timeout=15)


def is_sph_url(url: str) -> bool:
    """判断是否为视频号(微信频道)分享链接。"""
    return "weixin.qq.com/sph" in url or "channels.weixin.qq.com" in url


def parse_sph_url(url: str) -> dict:
    """用腾讯元宝解析视频号分享链接，返回 video_url / author / description 或抛异常。"""
    cookie = os.environ.get("HY_TOKEN", "")
    if not cookie:
        raise RuntimeError("HY_TOKEN 未配置（腾讯元宝 cookie，登录元宝后 F12 获取）")

    parse = _sph_parse_share_url(url, cookie)
    data = parse.get("data") or {}
    export_id = data.get("wx_export_id", "")
    playable = data.get("playable_url") or ""
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(playable).query)
    general_token = (qs.get("token") or [""])[0]
    eid = (qs.get("eid") or [""])[0] or export_id

    feed = _sph_get_feed_info(eid, general_token)
    feed_data = feed.get("data") or {}
    feed_info = feed_data.get("feedInfo") or {}
    return {
        "video_url": feed_info.get("videoUrl") or feed_info.get("originVideoUrl") or "",
        "author": (feed_data.get("authorInfo") or {}).get("nickname") or "",
        "description": feed_info.get("description") or "",
    }
