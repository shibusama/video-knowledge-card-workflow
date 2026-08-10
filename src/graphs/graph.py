from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput
)
from graphs.nodes.video_analysis_node import video_analysis_node
from graphs.nodes.summary_image_gen_node import summary_image_gen_node

# 创建状态图，指定全局状态、输入和输出结构
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# 添加节点
builder.add_node(
    "video_analysis",
    video_analysis_node,
    metadata={"type": "agent", "llm_cfg": "config/video_analysis_llm_cfg.json"}
)
builder.add_node(
    "summary_image_gen",
    summary_image_gen_node,
    metadata={"llm_cfg": "config/summary_image_gen_cfg.json"}
)

# 设置入口点
builder.set_entry_point("video_analysis")

# 添加边：视频分析 -> 总结图片生成 -> 结束
builder.add_edge("video_analysis", "summary_image_gen")
builder.add_edge("summary_image_gen", END)

# 编译图
main_graph = builder.compile()
