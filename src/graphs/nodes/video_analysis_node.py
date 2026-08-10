import os
import json
import re
import time
import requests
import logging
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from graphs.state import VideoAnalysisInput, VideoAnalysisOutput

logger = logging.getLogger(__name__)


def _extract_text(content) -> str:
    """安全提取LLM响应文本"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return " ".join(text_parts)
    return str(content)


def _is_douyin_url(url: str) -> bool:
    """判断是否为抖音链接"""
    return bool(re.search(r"(douyin\.com|v\.douyin)", url, re.IGNORECASE))


def _fetch_douyin_video_stream(page_url: str) -> str:
    """使用独立脚本抓取抖音视频的真实视频流URL"""
    import subprocess
    script_path = os.path.join(
        os.path.dirname(__file__), "_douyin_fetcher.py"
    )
    try:
        result = subprocess.run(
            ["python3", script_path, page_url],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            video_url = result.stdout.strip()
            if video_url:
                return video_url
        logger.warning(f"抖音抓流脚本失败: {result.stderr[:200]}")
        return ""
    except Exception as e:
        logger.warning(f"抖音抓流脚本异常: {e}")
        return ""


def _fetch_douyin_page_content(url: str) -> str:
    """获取抖音视频页面文本内容，使用FetchClient SDK"""
    from coze_coding_dev_sdk.fetch import FetchClient
    try:
        client = FetchClient()
        response = client.fetch(url=url)
        if response.status_code == 0:
            text_parts = []
            if response.title:
                text_parts.append(f"【视频标题】{response.title}")
            for item in response.content:
                if item.type == "text" and item.text:
                    text_parts.append(item.text)
            return "\n".join(text_parts) if text_parts else f"视频页面: {url}"
        else:
            return f"视频页面: {url}"
    except Exception:
        return f"视频页面: {url}"


def _parse_card_content_from_text(analysis_text: str) -> dict:
    """从LLM返回的文本中解析JSON卡片内容"""
    card_content = {}
    try:
        json_start = analysis_text.find("{")
        json_end = analysis_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = analysis_text[json_start:json_end]
            card_content = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    # 确保必要字段存在
    if "title" not in card_content:
        card_content["title"] = "视频内容总结"
    if "key_points" not in card_content:
        card_content["key_points"] = []
    if "summary" not in card_content:
        card_content["summary"] = analysis_text[:200] if analysis_text else ""
    if "tags" not in card_content:
        card_content["tags"] = []

    return card_content


def video_analysis_node(state: VideoAnalysisInput, config: RunnableConfig, runtime: Runtime[Context]) -> VideoAnalysisOutput:
    """
    title: 视频内容分析与知识提炼
    desc: 自动识别输入是抖音链接还是视频文件URL，分析内容并提炼出适合知识卡片展示的结构化文案（标题、要点、总结等）
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 从config的metadata读取LLM配置文件路径
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH", ""), config["metadata"]["llm_cfg"])
    with open(cfg_file, "r", encoding="utf-8") as fd:
        llm_cfg = json.load(fd)

    llm_config = llm_cfg.get("config", {})
    sp = llm_cfg.get("sp", "")
    up = llm_cfg.get("up", "")

    # 获取视频URL
    video_url = state.video_url.url

    # 初始化LLM客户端
    client = LLMClient(ctx=ctx)
    model_id = llm_config.get("model", "doubao-seed-2-0-pro-260215")
    temperature = llm_config.get("temperature", 0.3)
    max_completion_tokens = llm_config.get("max_completion_tokens", 4096)

    # 判断是否为抖音链接
    if _is_douyin_url(video_url):
        # === 抖音链接处理流程：先尝试Playwright抓取视频流，失败则回退到文本分析 ===

        # 尝试用Playwright抓取视频流
        video_stream_url = _fetch_douyin_video_stream(video_url)

        if video_stream_url:
            # 成功获取视频流，走多模态分析
            messages = [
                SystemMessage(content=sp),
                HumanMessage(content=[
                    {"type": "text", "text": up},
                    {"type": "video_url", "video_url": {"url": video_stream_url}}
                ])
            ]

            response = client.invoke(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens
            )

            analysis_text = _extract_text(response.content)
            if analysis_text.strip():
                card_content = _parse_card_content_from_text(analysis_text)
                return VideoAnalysisOutput(card_content=card_content)

        # 回退方案：web_fetch获取页面文本 → LLM提取内容
        page_content = _fetch_douyin_page_content(video_url)

        if not page_content.strip():
            page_content = f"视频链接: {video_url}"

        if len(page_content) > 8000:
            page_content = page_content[:8000]

        text_analysis_prompt = f"""请根据以下抖音视频页面内容，提取视频的核心信息，返回JSON格式：

{{
  "title": "视频标题/核心主题",
  "key_points": ["要点1", "要点2", "要点3", ...],
  "summary": "一句话总结（不超过30字）",
  "tags": ["标签1", "标签2", ...]
}}

页面内容：
{page_content}
"""

        messages = [
            SystemMessage(content="你是一个专业的内容分析助手，擅长从视频页面信息中提取核心内容，整理成知识卡片文案。"),
            HumanMessage(content=[{"type": "text", "text": text_analysis_prompt}])
        ]

        response = client.invoke(
            messages=messages,
            model=model_id,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens
        )

        analysis_text = _extract_text(response.content)
        card_content = _parse_card_content_from_text(analysis_text)

    else:
        # === 普通视频URL处理流程：多模态分析视频内容 ===
        messages = [
            SystemMessage(content=sp),
            HumanMessage(content=[
                {"type": "text", "text": up},
                {"type": "video_url", "video_url": {"url": video_url}}
            ])
        ]

        response = client.invoke(
            messages=messages,
            model=model_id,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens
        )

        analysis_text = _extract_text(response.content)

        if not analysis_text.strip():
            raise ValueError("视频内容分析结果为空，请检查视频链接是否有效")

        card_content = _parse_card_content_from_text(analysis_text)

    return VideoAnalysisOutput(card_content=card_content)
