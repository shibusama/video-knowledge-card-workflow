import os
import json
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import ImageGenerationClient
from graphs.state import SummaryImageGenInput, SummaryImageGenOutput


def summary_image_gen_node(state: SummaryImageGenInput, config: RunnableConfig, runtime: Runtime[Context]) -> SummaryImageGenOutput:
    """
    title: 总结图片生成
    desc: 根据视频分析结果生成高质量的总结图片，包含核心内容提示和视觉元素
    integrations: 图片生成
    """
    ctx = runtime.context

    # 从config的metadata读取图片生成配置
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH", ""), config["metadata"]["llm_cfg"])
    with open(cfg_file, "r", encoding="utf-8") as fd:
        img_cfg = json.load(fd)

    sp = img_cfg.get("sp", "")
    up = img_cfg.get("up", "")
    model_id = img_cfg.get("config", {}).get("model", "doubao-seedream-5-0-260128")
    size = img_cfg.get("config", {}).get("size", "2K")

    # 使用jinja2模板渲染用户提示词，将分析结果注入模板
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render(analysis_result=state.analysis_result)

    # 组合系统提示词和用户提示词作为最终的图片生成提示词
    image_prompt = f"{sp}\n\n{user_prompt_content}"

    # 初始化图片生成客户端
    client = ImageGenerationClient(ctx=ctx)

    # 生成总结图片
    response = client.generate(
        prompt=image_prompt,
        model=model_id,
        size=size,
        watermark=False
    )

    if not response.success:
        error_msgs = response.error_messages if hasattr(response, "error_messages") else ["未知错误"]
        raise ValueError(f"图片生成失败: {error_msgs}")

    # 获取生成的图片URL
    image_urls = response.image_urls
    if not image_urls:
        raise ValueError("图片生成成功但未返回图片URL")

    summary_image_url = image_urls[0]

    return SummaryImageGenOutput(summary_image_url=summary_image_url)
