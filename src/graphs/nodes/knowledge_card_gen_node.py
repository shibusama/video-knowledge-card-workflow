"""知识卡片生成节点 - 直接用大模型生成完整卡片图片"""

import io
import json
import logging
import os
import random
import tempfile
import time
from typing import Any, Dict, List, Optional

import requests
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from pydantic import BaseModel, Field

from graphs.state import KnowledgeCardGenInput, KnowledgeCardGenOutput
from utils.file.file import File, FileOps

logger = logging.getLogger(__name__)


def _build_card_prompt(
    title: str,
    key_points: List[str],
    summary: str,
    tags: Optional[List[str]] = None,
    style: str = "dark-tech",
) -> str:
    """根据风格和内容构建卡片生成提示词"""
    tags = tags or []

    # 要点列表格式化为文本
    points_text = "\n".join([f"{i+1}. {p}" for i, p in enumerate(key_points)])
    tags_text = "  ".join([f"#{t}" for t in tags[:4]])

    # 每个风格有多个变体描述，随机轮换
    style_variants = {
        "dark-tech": [
            "Dark tech style. Deep navy blue background with subtle data stream patterns, cyan and blue neon accents, futuristic and professional. Title in bright cyan (#00d4ff), key points in boxes with cyan borders, summary in a dark panel with cyan accent.",
            "Dark tech style. Midnight blue gradient background with subtle hexagonal grid lines, cool blue-toned lighting, clean and modern. Title in white with blue glow, key points in translucent dark glass boxes, summary in a blue gradient panel.",
            "Dark tech style. Charcoal black background with subtle circuit board patterns, emerald green and cyan neon accents, sleek and premium. Title in bright cyan, key points in dark bordered boxes with green accent dots, summary in a dark green-tinted panel.",
        ],
        "pop": [
            "Pop art style. Vibrant yellow background with bold red accents, comic-style halftone dots, energetic and playful. Title in bold red, key points in white boxes with thick black borders, summary in a black panel with white text.",
            "Pop art style. Bright magenta background with cyan and yellow contrasting elements, retro comic aesthetic, bold and loud. Title in white with black outline, key points in yellow boxes with red borders, summary in a cyan panel with black text.",
            "Pop art style. Hot pink background with geometric bursts in yellow and blue, pop culture inspired, vibrant and fun. Title in white with red shadow, key points in white boxes with dotted borders, summary in a bold yellow panel with black text.",
        ],
        "cyber": [
            "Cyberpunk style. Dark midnight background with neon cyan and magenta glows, digital grid patterns, holographic elements, futuristic. Title in bright cyan (#00e6ff) with glow, key points in dark boxes with cyan borders, summary in a purple-neon panel.",
            "Cyberpunk style. Near-black background with neon green and orange accents, rain-streaked city vibe, gritty and high-tech. Title in neon green with glow, key points in dark boxes with orange borders, summary in a neon orange panel.",
            "Cyberpunk style. Deep purple background with holographic blue and pink gradients, glitch effects, digital futuristic aesthetic. Title in holographic white-blue, key points in semi-transparent purple boxes with pink borders, summary in a holographic gradient panel.",
        ],
        "vaporwave": [
            "Vaporwave aesthetic. Purple-pink gradient background with retro grid lines, neon glow effects, 80s synthwave feel, dreamy. Title in hot pink neon, key points in semi-transparent boxes with pink borders, summary in a cyan-neon panel.",
            "Vaporwave aesthetic. Sunset gradient (orange to purple) background with palm trees silhouette, retro sunset vibe, nostalgic and dreamy. Title in gradient orange-pink, key points in frosted boxes with gold borders, summary in a sunset gradient panel.",
            "Vaporwave aesthetic. Deep teal to purple gradient background with geometric shapes, neon outlines, retro-futuristic. Title in neon pink, key points in boxes with teal borders and roman numerals, summary in a purple neon panel.",
        ],
        "glassmorphism": [
            "Glassmorphism style. Soft pastel gradient background (blue to purple), frosted glass effect panels, minimal and clean, light and airy. Title in dark navy, key points in frosted glass boxes with subtle borders, summary in a frosted glass panel.",
            "Glassmorphism style. Warm gradient background (peach to pink), frosted glass panels with soft shadows, elegant and modern. Title in dark purple, key points in translucent white glass panels with subtle shadows, summary in a larger glass panel.",
            "Glassmorphism style. Cool gradient background (teal to blue), frosted glass elements with light border, clean and sophisticated. Title in dark teal, key points in frosted glass cards with blur effect, summary in a prominent glass panel.",
        ],
        "bauhaus": [
            "Bauhaus design style. Cream white background with bold geometric elements in red, blue, yellow, and black. Clean lines, constructivist composition. Title in bold black, key points in white boxes with black borders and red accents, summary in a solid black panel with white text.",
            "Bauhaus design style. Light gray background with asymmetric geometric blocks in primary colors (red circle, blue square, yellow triangle). Modern art feel. Title in black bold sans-serif, key points in minimal boxes with colored left bars, summary in a bold yellow panel.",
            "Bauhaus design style. Off-white background with bold diagonal lines in red and black. Constructivist poster aesthetic. Title in bold black with red underline stripe, key points in clean white boxes with minimal borders, summary in a solid red panel with white text.",
        ],
    }

    # 如果 style 是 random，随机选一个风格
    all_styles = list(style_variants.keys())
    if style == "random" or style not in style_variants:
        style = random.choice(all_styles)

    # 从该风格的多组描述中随机选一个
    style_desc = random.choice(style_variants[style])

    # 随机选择一种布局，每次不一样
    layouts = [
        # 布局1: 经典列表
        """CARD LAYOUT (top to bottom):
1. Top section: A thin decorative line/accent across the top
2. Title area: The main title in large, bold font, centered
3. Content area: Key points listed vertically in individual bordered rounded boxes, each with a number prefix
4. Tags area: Small tag badges with hashtags, arranged horizontally
5. Bottom section: A highlighted summary panel with the brief statement""",

        # 布局2: 两列并排
        """CARD LAYOUT (top to bottom):
1. Title area: Large bold title at the top, centered with a decorative underline
2. Content area: Key points arranged in TWO COLUMNS side by side, each point in a small card/box, numbered
3. Tags area: Tags displayed as small pills/badges in a row
4. Bottom section: Full-width summary bar at the bottom with accent background""",

        # 布局3: 杂志风格
        """CARD LAYOUT (top to bottom):
1. Top section: Title in large serif-style font, with a decorative line below
2. Content area: Each key point styled as a "quote card" with a large number in the background, text overlaid
3. Tags area: Tags shown as small text links with dots between them
4. Bottom section: Summary in a pull-quote style box with a different background color""",

        # 布局4: 极简留白
        """CARD LAYOUT (top to bottom):
1. Title area: Clean minimal title at top-left, small and elegant
2. Divider: A thin horizontal line separating title from content
3. Content area: Key points listed with minimal styling - just a small dot and text, no boxes, lots of whitespace
4. Tags area: Minimal tags in small gray text
5. Bottom section: Summary in a simple thin-bordered box at the bottom, clean and understated""",

        # 布局5: 仪表盘网格
        """CARD LAYOUT (top to bottom):
1. Top section: A status-bar style decorative element at the very top
2. Title area: Bold title with a colored background strip/ribbon behind it
3. Content area: Key points in a "dashboard" style - each point in a square tile, arranged in a grid (2 columns), with a number in the corner
4. Tags area: Tags displayed as small colored badges at the bottom of the tile area
5. Bottom section: Summary in a horizontal gradient bar spanning the full width""",
    ]

    layout_desc = random.choice(layouts)

    prompt = f"""Create a vertical knowledge card (9:16 ratio, portrait orientation) as a high-quality PNG image.

STYLE: {style_desc}

The card MUST contain the following EXACT text content, rendered as CLEAR, READABLE Chinese text. Every character must be accurate - no typos, no substitutions, no missing strokes.

{layout_desc}

TEXT CONTENT (CRITICAL - render these EXACTLY):
Title: {title}

Key Points:
{points_text}

Summary: {summary}

Tags: {tags_text}

IMPORTANT REQUIREMENTS:
- All Chinese text MUST be perfectly rendered, clear, and readable
- Use proper Chinese fonts (simplified Chinese)
- Text should be well-spaced and easy to read
- The card should look professional and visually appealing
- 1080x1920 pixel resolution equivalent (9:16 portrait)
- High contrast between text and background for readability
- DO NOT use placeholder text - render the exact content provided above
- Each key point should be in its own distinct box/panel as described in the layout"""

    return prompt


def knowledge_card_gen_node(
    state: KnowledgeCardGenInput,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> KnowledgeCardGenOutput:
    """
    title: 生成知识卡片
    desc: 用大模型直接生成包含文字的完整知识卡片图片
    integrations: 图片生成大模型, 对象存储
    """
    ctx = runtime.context

    # 如果有错误，直接透传
    if state.error:
        return KnowledgeCardGenOutput(
            card_image_url="",
            card_content=state.card_content or {
                "title": "⚠️ 无法解析该链接",
                "key_points": ["该链接无法解析，请检查链接是否有效"],
                "summary": "请检查链接是否有效，或尝试更换其他链接",
                "tags": ["解析失败"],
            },
            error=state.error,
        )

    card_content = state.card_content or {}
    style = state.style or "dark-tech"

    title = card_content.get("title", "知识卡片")
    key_points = card_content.get("key_points", [])
    summary = card_content.get("summary", "")
    tags = card_content.get("tags", [])

    # ── 构建完整卡片提示词 ──
    card_prompt = _build_card_prompt(
        title=title,
        key_points=key_points,
        summary=summary,
        tags=tags,
        style=style,
    )

    # ── 用大模型直接生成完整卡片 ──
    try:
        from coze_coding_dev_sdk import ImageGenerationClient

        image_model = os.getenv("IMAGE_GEN_MODEL") or "doubao-seedream-5-0-260128"

        img_client = ImageGenerationClient()
        response = img_client.generate(
            prompt=card_prompt,
            model=image_model,
            size="1440x2560",
        )

        # 解析返回的图片URL
        card_url_orig = None
        if hasattr(response, "image_urls") and response.image_urls:
            card_url_orig = response.image_urls[0]
        elif isinstance(response, dict):
            urls = response.get("image_urls") or response.get("urls") or response.get("data", [])
            if isinstance(urls, list) and urls:
                card_url_orig = urls[0] if isinstance(urls[0], str) else urls[0].get("url")

        if not card_url_orig:
            raise ValueError("卡片生成失败：未返回图片URL")

        logger.info(f"卡片已生成: {card_url_orig[:80]}...")

    except Exception as e:
        logger.error(f"卡片生成失败: {e}")
        return KnowledgeCardGenOutput(
            card_image_url="",
            card_content=card_content,
            error=f"卡片生成失败: {e}",
        )

    # ── 下载并上传到对象存储 ──
    try:
        # 下载图片
        resp = requests.get(card_url_orig, timeout=60)
        resp.raise_for_status()

        from coze_coding_dev_sdk import S3SyncStorage

        storage = S3SyncStorage()

        file_data = resp.content
        remote_path = f"knowledge_card_{int(time.time() * 1000)}.png"
        object_key = storage.upload_file(
            file_content=file_data,
            file_name=remote_path,
            content_type="image/png",
        )

        if not object_key:
            raise ValueError("上传对象存储失败：未返回object_key")

        card_url = storage.generate_presigned_url(
            key=object_key,
            expire_time=86400 * 7
        )

        logger.info(f"卡片已上传: {card_url[:80]}...")

        return KnowledgeCardGenOutput(
            card_image_url=card_url,
            card_content=card_content,
            error="",
        )

    except Exception as e:
        logger.error(f"上传对象存储失败: {e}")
        return KnowledgeCardGenOutput(
            card_image_url="",
            card_content=card_content,
            error=f"上传对象存储失败: {e}",
        )