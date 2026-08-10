import os, sys, json
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from unittest.mock import MagicMock, PropertyMock

from graphs.nodes.knowledge_card_gen_node import knowledge_card_gen_node

# 构造输入
class MockInput(BaseModel):
    card_content: dict = Field(default={
        "title": "千问发布Image3.0 Pro图像模型",
        "key_points": [
            "千问推出全新Image3.0 Pro图像生成模型，支持4K高清画质",
            "定价每张0.18元，引发网友对AI生图价格的热议",
            "网友吐槽：比GPT-4o生图还贵，国产模型定价偏高",
            "评论期待像DeepSeek一样降低AI使用门槛",
            "开市科技信息旗下账号发布，粉丝1.6万获赞35.8万"
        ],
        "summary": "千问发布Image3.0 Pro图像模型，4K画质但定价0.18元/张引发价格争议",
        "tags": ["AI", "图像生成", "千问", "大模型", "Image3.0"]
    })
    style: str = "dark-tech"

class MockConfig(BaseModel):
    configurable: dict = {}
    metadata: Optional[dict] = {"llm_cfg": "config/summary_image_gen_cfg.json"}

# 模拟 runtime 和 context
ctx = MagicMock(spec=Context)
ctx.logid = PropertyMock(return_value="test-logid")
type(ctx).logid = PropertyMock(return_value="test-logid")

runtime = MagicMock(spec=Runtime)
runtime.context = ctx

result = knowledge_card_gen_node(
    state=MockInput(),
    config=MockConfig(),
    runtime=runtime
)

print(f"✅ 卡片生成成功！")
print(f"图片URL: {result.card_image_url}")
print(f"内容: {json.dumps(result.card_content, ensure_ascii=False, indent=2)}")
