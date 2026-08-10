"""
从抖音视频内容直接生成知识卡片
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "src"))

from graphs.state import KnowledgeCardGenInput, KnowledgeCardGenOutput
from graphs.nodes.knowledge_card_gen_node import knowledge_card_gen_node
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

# 从抖音页面解析到的内容
card_content = {
    "title": "🏆 GitHub本周7大热门项目",
    "key_points": [
        "j code：轻量AI编程工作台，解决多Agent卡顿问题",
        "open code review：阿里开源AI代码检查工具",
        "i have ADHD：Agent先说结论少绕弯，需求真实",
        "book to scale：技术书/PDF转Agent可调用Skill",
        "Reverse skill：AI安全研究技能路由器",
        "bus：人与AI Agent共用团队工作区",
        "AI for beginners：微软12周24节免费AI课程"
    ],
    "summary": "AI竞争从'谁更会聊天'转向'谁能把工作真正做完'，7个开源项目各具亮点",
    "tags": ["GitHub", "开源项目", "AI", "编程"]
}

# 构造输入
node_input = KnowledgeCardGenInput(
    card_content=card_content,
    style="dark-tech"
)

# 构造正确的 Runtime[Context]
ctx = Context(run_id="test", space_id="test", project_id="test")
runtime = Runtime[Context](context=ctx)

config = RunnableConfig()

print("🚀 正在生成知识卡片（dark-tech 深色科技风格）...")
result = knowledge_card_gen_node(node_input, config, runtime)
print(f"\n✅ 生成成功！")
print(f"📎 卡片图片URL: {result.card_image_url}")
print(f"\n卡片内容:")
print(json.dumps(card_content, ensure_ascii=False, indent=2))