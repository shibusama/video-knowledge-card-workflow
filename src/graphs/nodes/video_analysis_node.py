import os
import json
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from graphs.state import VideoAnalysisInput, VideoAnalysisOutput


def video_analysis_node(state: VideoAnalysisInput, config: RunnableConfig, runtime: Runtime[Context]) -> VideoAnalysisOutput:
    """
    title: 视频内容分析
    desc: 使用多模态大模型分析视频内容，提取核心信息（主要观点、关键画面、重要标题等）
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

    # 使用jinja2模板渲染用户提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render(video_url=video_url)

    # 初始化LLM客户端
    client = LLMClient(ctx=ctx)

    # 构建消息：系统提示词 + 视频内容分析请求
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=[
            {"type": "text", "text": user_prompt_content},
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
    analysis_text = ""
    if isinstance(response.content, str):
        analysis_text = response.content
    elif isinstance(response.content, list):
        if response.content and isinstance(response.content[0], str):
            analysis_text = " ".join(response.content)
        else:
            text_parts = [
                item.get("text", "")
                for item in response.content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            analysis_text = " ".join(text_parts)
    else:
        analysis_text = str(response.content)

    if not analysis_text.strip():
        raise ValueError("视频内容分析结果为空，请检查视频链接是否有效")

    return VideoAnalysisOutput(analysis_result=analysis_text)
