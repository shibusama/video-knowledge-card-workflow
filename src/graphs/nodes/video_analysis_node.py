import os
import json
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from graphs.state import VideoAnalysisInput, VideoAnalysisOutput


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


def video_analysis_node(state: VideoAnalysisInput, config: RunnableConfig, runtime: Runtime[Context]) -> VideoAnalysisOutput:
    """
    title: 视频内容分析与知识提炼
    desc: 使用多模态大模型分析视频内容，提炼出适合知识卡片展示的结构化文案（标题、要点、总结等）
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

    # 构建消息：系统提示词 + 视频内容分析请求
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=[
            {"type": "text", "text": up},
            {"type": "video_url", "video_url": {"url": video_url}}
        ])
    ]

    # 调用大模型分析视频
    model_id = llm_config.get("model", "doubao-seed-2-0-pro-260215")
    temperature = llm_config.get("temperature", 0.3)
    max_completion_tokens = llm_config.get("max_completion_tokens", 4096)

    response = client.invoke(
        messages=messages,
        model=model_id,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens
    )

    # 安全提取响应内容
    analysis_text = _extract_text(response.content)

    if not analysis_text.strip():
        raise ValueError("视频内容分析结果为空，请检查视频链接是否有效")

    # 尝试解析JSON格式的输出
    card_content = {}
    try:
        # 尝试从文本中提取JSON
        json_start = analysis_text.find("{")
        json_end = analysis_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = analysis_text[json_start:json_end]
            card_content = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        # 如果不是JSON，构造默认结构
        card_content = {
            "title": "视频内容总结",
            "key_points": [analysis_text[:200]],
            "summary": analysis_text[:100],
            "raw_analysis": analysis_text
        }

    # 确保必要字段存在
    if "title" not in card_content:
        card_content["title"] = "视频内容总结"
    if "key_points" not in card_content:
        card_content["key_points"] = [card_content.get("summary", analysis_text[:100])]
    if "summary" not in card_content:
        card_content["summary"] = analysis_text[:100]

    return VideoAnalysisOutput(card_content=card_content)
