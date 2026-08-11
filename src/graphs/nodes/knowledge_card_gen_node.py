import os
import json
import uuid
import shutil
import logging
import requests
from io import BytesIO
from typing import List, Dict, Any, Optional
from PIL import Image
from playwright.sync_api import sync_playwright
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import ImageGenerationClient
from storage.s3.s3_storage import S3SyncStorage
from graphs.state import KnowledgeCardGenInput, KnowledgeCardGenOutput

logger = logging.getLogger(__name__)


def _ensure_chromium_installed() -> None:
    """自动检查并安装 Playwright Chromium 浏览器（部署环境没有时自动下载）"""
    import subprocess
    import sys
    from pathlib import Path

    # 检查浏览器是否已安装
    chromium_path = Path.home() / ".cache" / "ms-playwright"
    if not any(chromium_path.glob("chromium*")):
        logger.info("Playwright Chromium 未安装，正在自动下载...")
        try:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
                check=True, capture_output=True, text=True, timeout=120
            )
            logger.info("Playwright Chromium 安装成功")
        except Exception as e:
            logger.error(f"Playwright 安装失败: {e}")
            raise RuntimeError("自动安装 Playwright Chromium 失败，请检查网络或手动安装")


# ============================================================
# 风格配置 - 基于 video-knowledge-card 技能
# ============================================================
STYLE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "dark-tech": {
        "name": "深色科技",
        "bg_prompt_suffix": "deep blue-purple gradient background, futuristic tech style, glowing particles, no text, no letters, no watermark, pure background image",
        "css": """
            body { background: linear-gradient(160deg, #0b1026, #131a3a, #1b1040); font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
            .card { padding: 60px 50px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }
            .title { font-size: 56px; font-weight: 900; background: linear-gradient(90deg, #00d4ff, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 40px; line-height: 1.3; }
            .point { background: rgba(255,255,255,0.08); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; padding: 20px 28px; margin-bottom: 16px; color: #e0e7ff; font-size: 26px; line-height: 1.5; }
            .point::before { content: '◆'; color: #00d4ff; margin-right: 12px; }
            .summary { margin-top: 30px; padding: 24px 28px; background: rgba(0,212,255,0.08); border-left: 4px solid #00d4ff; border-radius: 0 12px 12px 0; color: #94a3b8; font-size: 22px; line-height: 1.6; }
        """
    },
    "pop": {
        "name": "波普",
        "bg_prompt_suffix": "pop art style background, bold primary colors, Ben-Day dots pattern, comic style, no text, no letters, no watermark, pure background image",
        "css": """
            body { background: #FFD700; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
            .card { padding: 60px 50px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }
            .title { font-size: 58px; font-weight: 900; color: #FF3B30; -webkit-text-stroke: 3px #111; text-shadow: 7px 7px 0 #111; margin-bottom: 40px; transform: rotate(-1deg); line-height: 1.3; }
            .point { background: #fff; border: 5px solid #111; box-shadow: 7px 7px 0 #111; padding: 18px 24px; margin-bottom: 18px; color: #111; font-size: 26px; font-weight: 700; transform: rotate(1deg); line-height: 1.4; }
            .point:nth-child(odd) { transform: rotate(-1deg); background: #FF6B9D; }
            .point:nth-child(even) { background: #007AFF; color: #fff; }
            .summary { margin-top: 30px; padding: 20px 24px; background: #7CFC00; border: 5px solid #111; box-shadow: 5px 5px 0 #111; color: #111; font-size: 22px; font-weight: 700; transform: rotate(-0.5deg); }
        """
    },
    "cyber": {
        "name": "赛博酷炫",
        "bg_prompt_suffix": "cyberpunk neon background, dark with glowing cyan and purple neon lines, futuristic grid, no text, no letters, no watermark, pure background image",
        "css": """
            body { background: #0a0a1a; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
            .card { padding: 60px 50px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }
            .title { font-size: 56px; font-weight: 900; color: #00e5ff; text-shadow: 0 0 10px #00e5ff, 0 0 20px #00e5ff, 0 0 40px #a855f7; margin-bottom: 40px; line-height: 1.3; }
            .point { background: rgba(0,229,255,0.05); border: 2px solid rgba(0,229,255,0.35); box-shadow: 0 0 26px rgba(0,229,255,0.12); border-radius: 8px; padding: 20px 28px; margin-bottom: 16px; color: #e0f7ff; font-size: 26px; line-height: 1.5; }
            .point::before { content: '▸'; color: #a855f7; margin-right: 12px; text-shadow: 0 0 8px #a855f7; }
            .summary { margin-top: 30px; padding: 24px 28px; border: 1px solid rgba(168,85,247,0.5); box-shadow: 0 0 20px rgba(168,85,247,0.2); border-radius: 8px; color: #c4b5fd; font-size: 22px; line-height: 1.6; }
        """
    },
    "vaporwave": {
        "name": "蒸汽波",
        "bg_prompt_suffix": "vaporwave aesthetic background, pink and blue gradient, retro grid perspective, sunset glow, neon palm trees silhouette, no text, no letters, no watermark, pure background image",
        "css": """
            body { background: linear-gradient(180deg, #1a0533, #2d1b69, #ff71ce); font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
            .card { padding: 60px 50px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }
            .title { font-size: 56px; font-weight: 900; color: #fff; text-shadow: 0 0 10px #fff, 0 0 20px #ff71ce, 0 0 40px #01cdfe, 0 0 60px #b967ff; margin-bottom: 40px; line-height: 1.3; }
            .point { background: rgba(255,255,255,0.1); border: 2px solid rgba(255,113,206,0.5); box-shadow: 0 0 15px rgba(1,205,254,0.3); border-radius: 12px; padding: 20px 28px; margin-bottom: 16px; color: #fff; font-size: 26px; line-height: 1.5; }
            .point::before { content: '★'; color: #05ffa1; margin-right: 12px; }
            .summary { margin-top: 30px; padding: 24px 28px; background: rgba(185,103,255,0.2); border: 1px solid #b967ff; border-radius: 12px; color: #e0c3fc; font-size: 22px; line-height: 1.6; }
        """
    },
    "glassmorphism": {
        "name": "玻璃拟态",
        "bg_prompt_suffix": "glassmorphism style background, colorful blurred light orbs, soft gradient with purple blue pink blobs, no text, no letters, no watermark, pure background image",
        "css": """
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
            .card { padding: 60px 50px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }
            .title { font-size: 54px; font-weight: 800; color: #fff; margin-bottom: 40px; line-height: 1.3; text-shadow: 0 2px 10px rgba(0,0,0,0.2); }
            .point { background: rgba(255,255,255,0.2); backdrop-filter: blur(22px); saturate(160%); -webkit-backdrop-filter: blur(22px); border: 1px solid rgba(255,255,255,0.3); box-shadow: inset 0 1px 0 rgba(255,255,255,0.4); border-radius: 20px; padding: 22px 28px; margin-bottom: 16px; color: #fff; font-size: 26px; line-height: 1.5; }
            .summary { margin-top: 30px; padding: 24px 28px; background: rgba(255,255,255,0.15); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); border: 1px solid rgba(255,255,255,0.25); border-radius: 16px; color: rgba(255,255,255,0.9); font-size: 22px; line-height: 1.6; }
        """
    },
    "bauhaus": {
        "name": "包豪斯",
        "bg_prompt_suffix": "bauhaus style background, geometric shapes, primary colors red yellow blue, black and white, clean modernist composition, no text, no letters, no watermark, pure background image",
        "css": """
            body { background: #F5F5F0; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
            .card { padding: 60px 50px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }
            .title { font-size: 56px; font-weight: 900; color: #111; margin-bottom: 40px; line-height: 1.3; border-bottom: 6px solid #E03A3E; padding-bottom: 16px; }
            .point { background: #fff; border: 3px solid #111; box-shadow: 5px 5px 0 #111; padding: 18px 24px; margin-bottom: 18px; color: #111; font-size: 26px; font-weight: 600; line-height: 1.4; }
            .point:nth-child(1) { border-left: 8px solid #E03A3E; }
            .point:nth-child(2) { border-left: 8px solid #F4D03F; }
            .point:nth-child(3) { border-left: 8px solid #1C5AA3; }
            .point:nth-child(4) { border-left: 8px solid #E03A3E; }
            .point:nth-child(5) { border-left: 8px solid #F4D03F; }
            .summary { margin-top: 30px; padding: 20px 24px; background: #111; color: #fff; font-size: 22px; font-weight: 600; }
        """
    }
}


def _generate_bg_prompt(card_content: Dict[str, Any], style: str) -> str:
    """根据内容生成背景图提示词"""
    style_cfg = STYLE_CONFIGS.get(style, STYLE_CONFIGS["dark-tech"])
    title = card_content.get("title", "")
    # 构建背景提示词：基于内容主题 + 风格后缀
    bg_prompt = f"Abstract artistic background for knowledge card about '{title}', {style_cfg['bg_prompt_suffix']}"
    return bg_prompt


def _build_html(card_content: Dict[str, Any], style: str) -> str:
    """构建知识卡片HTML"""
    style_cfg = STYLE_CONFIGS.get(style, STYLE_CONFIGS["dark-tech"])
    css = style_cfg["css"]

    title = card_content.get("title", "视频知识总结")
    key_points: List[str] = card_content.get("key_points", [])
    summary = card_content.get("summary", "")

    # 限制要点数量（4-7个）
    points = key_points[:7] if len(key_points) > 7 else key_points
    if not points:
        points = ["暂无要点"]

    # 构建要点HTML
    points_html = "\n".join([f'<div class="point">{p}</div>' for p in points])

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1080px; height: 1920px; overflow: hidden; }}
{css}
</style>
</head>
<body>
<div class="card">
    <div class="title">{title}</div>
    {points_html}
    <div class="summary">{summary}</div>
</div>
</body>
</html>"""
    return html


def knowledge_card_gen_node(state: KnowledgeCardGenInput, config: RunnableConfig, runtime: Runtime[Context]) -> KnowledgeCardGenOutput:
    """
    title: 知识卡片生成
    desc: 采用混合方案生成知识卡片：AI生成风格化背景 + HTML/CSS渲染文字内容 + Playwright截图合成，确保文字100%准确
    integrations: 图片生成
    """
    ctx = runtime.context
    card_content = state.card_content
    style = state.style

    # ========== 如果上游有错误，直接跳过卡片生成 ==========
    if state.error:
        logger.warning(f"上游检测到错误，跳过卡片生成: {state.error}")
        return KnowledgeCardGenOutput(error=state.error)
    # ====================================================

    # 获取风格配置
    style_cfg = STYLE_CONFIGS.get(style, STYLE_CONFIGS["dark-tech"])

    # ========== 步骤1: 生成风格化背景 ==========
    bg_prompt = _generate_bg_prompt(card_content, style)
    img_client = ImageGenerationClient(ctx=ctx)

    # 优先使用环境变量覆盖图片生成模型，否则用默认的 Seedream 5.0
    image_model = os.getenv("IMAGE_GEN_MODEL") or "doubao-seedream-5-0-260128"
    bg_response = img_client.generate(
        prompt=bg_prompt,
        model=image_model,
        size="2K",
        watermark=False
    )

    if not bg_response.success:
        raise ValueError(f"背景图生成失败: {bg_response.error_messages}")

    bg_url = bg_response.image_urls[0]

    # ========== 步骤2: 下载并缩放背景到 1080x1920 ==========
    bg_img_path = f"/tmp/bg_{uuid.uuid4().hex[:8]}.png"
    bg_data = requests.get(bg_url, timeout=60).content
    with open(bg_img_path, "wb") as f:
        f.write(bg_data)

    # 使用PIL缩放到目标尺寸
    target_size = (1080, 1920)
    img = Image.open(bg_img_path)
    img = img.resize(target_size, Image.Resampling.LANCZOS)
    img.save(bg_img_path, "PNG")

    # ========== 步骤3: 构建HTML（使用背景图 + 叠字） ==========
    style_css = style_cfg["css"]
    # 修改CSS，添加背景图
    css_with_bg = style_css.replace(
        "body {",
        f"body {{ background-image: url('file://{bg_img_path}'); background-size: cover; background-position: center;"
    )

    title = card_content.get("title", "视频知识总结")
    key_points: List[str] = card_content.get("key_points", [])
    summary_text = card_content.get("summary", "")
    points = key_points[:7] if len(key_points) > 7 else key_points
    if not points:
        points = ["暂无要点"]

    points_html = "\n".join([f'<div class="point">{p}</div>' for p in points])

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1080px; height: 1920px; overflow: hidden; background-image: url('file://{bg_img_path}'); background-size: cover; background-position: center; font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif; }}
{style_css.split('body {')[1].split('}')[0] if 'body {' in style_css else ''}
.card {{ padding: 60px 50px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }}
</style>
<style>
{style_css}
</style>
</head>
<body>
<div class="card">
    <div class="title">{title}</div>
    {points_html}
    <div class="summary">{summary_text}</div>
</div>
</body>
</html>"""

    # ========== 步骤4: 使用Playwright截图 ==========
    card_output_path = f"/tmp/knowledge_card_{uuid.uuid4().hex[:8]}.png"

    # 自动安装 Playwright 浏览器（如果部署环境没装）
    _ensure_chromium_installed()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.set_content(html_content)
        # 等待字体和图片加载
        page.wait_for_timeout(1000)
        page.screenshot(path=card_output_path, full_page=False)
        browser.close()

    # ========== 步骤5: 上传卡片图片到对象存储 ==========
    card_image_url = ""
    try:
        # 使用S3存储上传
        s3_storage = S3SyncStorage(access_key="", secret_key="", bucket_name="")
        with open(card_output_path, "rb") as f:
            file_content = f.read()
        file_key = s3_storage.upload_file(
            file_content=file_content,
            file_name="knowledge_card.png",
            content_type="image/png"
        )
        # 生成签名URL
        card_image_url = s3_storage.generate_presigned_url(key=file_key, expire_time=86400)
        logger.info(f"卡片图片已上传到对象存储: {file_key}")
    except Exception as e:
        logger.warning(f"上传到对象存储失败，使用本地路径: {e}")
        # 降级：复制到assets目录
        workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
        assets_dir = os.path.join(workspace_path, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        final_path = os.path.join(assets_dir, f"knowledge_card_{uuid.uuid4().hex[:8]}.png")
        shutil.copy2(card_output_path, final_path)
        card_image_url = f"file://{final_path}"

    return KnowledgeCardGenOutput(card_image_url=card_image_url)
