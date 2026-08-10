import os, sys, json, base64
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from pydantic import BaseModel, Field
from typing import Optional, Literal
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from unittest.mock import MagicMock

# 导入节点
from graphs.nodes.knowledge_card_gen_node import knowledge_card_gen_node

# 构造输入
class MockInput(BaseModel):
    card_content: dict = Field(default={
        "title": "千问发布Image3.0 Pro图像模型",
        "key_points": [
            "千问推出全新Image3.0 Pro图像生成模型",
            "支持4K高清图像生成，画质大幅提升",
            "定价每张0.18元，引发网友热议",
            "相比GPT-4o生图价格更高，被指定价偏高",
            "网友期望像DeepSeek一样降低使用门槛"
        ],
        "summary": "千问发布Image3.0 Pro图像模型，4K画质但定价0.18元/张引发价格争议",
        "tags": ["AI", "图像生成", "千问", "大模型"]
    })
    style: str = "dark-tech"

class MockConfig(BaseModel):
    configurable: dict = {}
    metadata: Optional[dict] = {"llm_cfg": "config/summary_image_gen_cfg.json"}

# 创建 runtime mock
ctx = MagicMock(spec=Context)
runtime = MagicMock(spec=Runtime)
runtime.context = ctx

# 执行节点
result = knowledge_card_gen_node(
    state=MockInput(),
    config=MockConfig(),
    runtime=runtime
)

print(f"\n✅ 卡片生成成功！")
print(f"图片URL: {result.card_image_url}")
print(f"内容: {json.dumps(result.card_content, ensure_ascii=False, indent=2)}")
