"""知识卡片生成节点 - 使用Pillow渲染文字（无需浏览器）"""

import io
import json
import logging
import math
import os
import re
import tempfile
import time
from typing import Any, Dict, List, Optional

import requests
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from pydantic import BaseModel, Field

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from graphs.state import KnowledgeCardGenInput, KnowledgeCardGenOutput
from utils.file.file import File, FileOps

logger = logging.getLogger(__name__)

# ── 字体配置 ──
FONT_DIR = "/usr/share/fonts/truetype/wqy"
FONT_REGULAR = os.path.join(FONT_DIR, "wqy-microhei.ttc")
FONT_BOLD = os.path.join(FONT_DIR, "wqy-zenhei.ttc")

# ── 卡片尺寸 ──
CARD_WIDTH = 1080
CARD_HEIGHT = 1920

# ── 风格颜色配置 ──
STYLE_COLORS: Dict[str, Dict[str, Any]] = {
    "dark-tech": {
        "overlay": (10, 15, 36, 160),
        "title": (0, 212, 255),
        "point_bg": (0, 212, 255, 15),
        "point_border": (0, 212, 255),
        "point_text": (200, 220, 255),
        "point_accent": (0, 212, 255),
        "summary_bg": (0, 212, 255, 25),
        "summary_border": (0, 212, 255),
        "summary_text": (148, 163, 184),
        "accent_color": (168, 85, 247),
        "title_glow": True,
    },
    "pop": {
        "overlay": (255, 200, 0, 140),
        "title": (220, 40, 40),
        "point_bg": (255, 255, 255, 200),
        "point_border": (30, 30, 30),
        "point_text": (30, 30, 30),
        "point_accent": (220, 40, 40),
        "summary_bg": (30, 30, 30, 220),
        "summary_border": (30, 30, 30),
        "summary_text": (255, 255, 200),
        "accent_color": (220, 40, 40),
        "title_glow": False,
    },
    "cyber": {
        "overlay": (5, 5, 20, 170),
        "title": (0, 230, 255),
        "point_bg": (0, 230, 255, 12),
        "point_border": (0, 230, 255),
        "point_text": (190, 220, 255),
        "point_accent": (180, 50, 255),
        "summary_bg": (180, 50, 255, 25),
        "summary_border": (180, 50, 255),
        "summary_text": (160, 180, 220),
        "accent_color": (180, 50, 255),
        "title_glow": True,
    },
    "vaporwave": {
        "overlay": (80, 20, 120, 160),
        "title": (255, 120, 220),
        "point_bg": (255, 120, 220, 15),
        "point_border": (255, 120, 220),
        "point_text": (220, 190, 255),
        "point_accent": (0, 255, 200),
        "summary_bg": (0, 255, 200, 20),
        "summary_border": (0, 255, 200),
        "summary_text": (180, 220, 255),
        "accent_color": (0, 255, 200),
        "title_glow": True,
    },
    "glassmorphism": {
        "overlay": (255, 255, 255, 60),
        "title": (60, 60, 80),
        "point_bg": (255, 255, 255, 180),
        "point_border": (255, 255, 255, 200),
        "point_text": (60, 60, 80),
        "point_accent": (100, 120, 220),
        "summary_bg": (255, 255, 255, 160),
        "summary_border": (255, 255, 255, 200),
        "summary_text": (80, 80, 100),
        "accent_color": (100, 120, 220),
        "title_glow": False,
    },
    "bauhaus": {
        "overlay": (255, 250, 240, 160),
        "title": (30, 30, 30),
        "point_bg": (255, 255, 255, 200),
        "point_border": (30, 30, 30),
        "point_text": (30, 30, 30),
        "point_accent": (200, 50, 50),
        "summary_bg": (30, 30, 30, 220),
        "summary_border": (30, 30, 30),
        "summary_text": (255, 250, 240),
        "accent_color": (50, 100, 200),
        "title_glow": False,
    },
}

# ── 背景提示词后缀 ──
STYLE_BG_PROMPTS: Dict[str, str] = {
    "dark-tech": (
        "Technology data stream background, dark blue and deep purple tones, "
        "abstract digital patterns, grid lines, subtle glow effects, "
        "futuristic atmosphere, clean and professional, 2K resolution"
    ),
    "pop": (
        "Pop art style background, vibrant yellow and red, bold geometric shapes, "
        "halftone dots pattern, comic book aesthetic, energetic and fun, "
        "bright and colorful, 2K resolution"
    ),
    "cyber": (
        "Cyberpunk city background, neon cyan and magenta, dark atmosphere, "
        "digital rain, holographic grid, futuristic urban landscape, "
        "glowing neon signs, high contrast, 2K resolution"
    ),
    "vaporwave": (
        "Vaporwave aesthetic background, sunset purple and pink gradients, "
        "neon grid lines, retro 80s synthwave, palm trees silhouette, "
        "glitch art effects, dreamy nostalgic atmosphere, 2K resolution"
    ),
    "glassmorphism": (
        "Soft gradient background in pastel blue and purple tones, "
        "smooth abstract shapes, frosted glass texture, "
        "minimalist and clean, gentle light effects, 2K resolution"
    ),
    "bauhaus": (
        "Bauhaus design style background, cream and white base, "
        "bold geometric shapes in red, blue, yellow, and black, "
        "clean lines, constructivist composition, artistic, 2K resolution"
    ),
}


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """加载中文字体"""
    font_path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()


def _draw_rounded_rect(
    draw: Any,
    xy: tuple,
    radius: int,
    fill: Optional[tuple] = None,
    outline: Optional[tuple] = None,
    width: int = 1,
):
    """画圆角矩形"""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _draw_text_with_glow(
    draw: Any,
    xy: tuple,
    text: str,
    font: Any,
    fill: tuple,
    glow_color: tuple = (0, 0, 0),
    glow_radius: int = 8,
    anchor: str = "la",
):
    """画带发光效果的文字（多层叠加模拟发光）"""
    x, y = xy
    # 发光层：画多层半透明文字
    for offset in range(glow_radius, 0, -2):
        alpha = max(20, 60 - offset * 3)
        glow_fill = (glow_color[0], glow_color[1], glow_color[2], alpha)
        draw.text((x, y), text, font=font, fill=glow_fill, anchor=anchor)
    for offset in range(glow_radius, 0, -2):
        alpha = max(20, 60 - offset * 3)
        glow_fill = (glow_color[0], glow_color[1], glow_color[2], alpha)
        draw.text((x - offset, y), text, font=font, fill=glow_fill, anchor=anchor)
        draw.text((x + offset, y), text, font=font, fill=glow_fill, anchor=anchor)
    # 主文字层
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def _wrap_text(draw: Any, text: str, font: Any, max_width: int) -> List[str]:
    """自动换行"""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = list(paragraph)
        current_line = ""
        for char in words:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
    return lines


def _render_card(
    background: Image.Image,
    title: str,
    key_points: List[str],
    summary: str,
    tags: Optional[List[str]] = None,
    style: str = "dark-tech",
) -> Image.Image:
    """用Pillow在背景图上渲染卡片文字"""
    colors = STYLE_COLORS.get(style, STYLE_COLORS["dark-tech"])
    bg_w, bg_h = background.size

    # 缩放到标准尺寸
    bg = background.resize((CARD_WIDTH, CARD_HEIGHT), Image.Resampling.LANCZOS)

    # 创建绘图层（RGBA，支持透明）
    canvas = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # ── 1. 半透明遮罩 ──
    overlay = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), colors["overlay"])
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # ── 2. 顶部装饰线 ──
    _draw_rounded_rect(
        draw,
        (80, 60, CARD_WIDTH - 80, 64),
        radius=2,
        fill=colors["accent_color"] + (200,) if len(colors["accent_color"]) == 3 else colors["accent_color"],
    )

    # ── 3. 标题 ──
    title_font = _load_font(76, bold=True)
    title_color = colors["title"]
    if len(title_color) == 3:
        title_color = title_color + (255,)

    # 标题发光效果
    if colors.get("title_glow", False):
        _draw_text_with_glow(
            draw,
            (CARD_WIDTH // 2, 160),
            title,
            title_font,
            fill=title_color,
            glow_color=title_color[:3],
            glow_radius=12,
            anchor="ma",
        )
    else:
        draw.text((CARD_WIDTH // 2, 160), title, font=title_font, fill=title_color, anchor="ma")

    # 标题下划线
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    line_y = 160 + (title_bbox[3] - title_bbox[1]) // 2 + 20
    _draw_rounded_rect(
        draw,
        (CARD_WIDTH // 2 - title_w // 2 - 20, line_y, CARD_WIDTH // 2 + title_w // 2 + 20, line_y + 4),
        radius=2,
        fill=colors["accent_color"] + (200,) if len(colors["accent_color"]) == 3 else colors["accent_color"],
    )

    # ── 4. 要点列表 ──
    point_font = _load_font(38)
    point_text_color = colors["point_text"]
    if len(point_text_color) == 3:
        point_text_color = point_text_color + (255,)

    point_accent = colors["point_accent"]
    if len(point_accent) == 3:
        point_accent = point_accent + (255,)

    point_bg = colors["point_bg"]
    if len(point_bg) == 3:
        point_bg = point_bg + (255,)

    point_border = colors["point_border"]
    if len(point_border) == 3:
        point_border = point_border + (255,)

    start_y = 280
    box_x1 = 100
    box_x2 = CARD_WIDTH - 100
    box_max_w = box_x2 - box_x1 - 40

    for i, point in enumerate(key_points):
        # 自动换行
        lines = _wrap_text(draw, point, point_font, box_max_w)
        line_height = 52
        box_h = max(80, len(lines) * line_height + 40)

        py = start_y + i * (box_h + 20)

        # 要点背景框
        _draw_rounded_rect(
            draw,
            (box_x1, py, box_x2, py + box_h),
            radius=16,
            fill=point_bg,
            outline=point_border,
            width=2,
        )

        # 左侧装饰竖条
        _draw_rounded_rect(
            draw,
            (box_x1 + 8, py + 12, box_x1 + 12, py + box_h - 12),
            radius=4,
            fill=point_accent,
        )

        # 序号
        num_font = _load_font(32, bold=True)
        num_text = f"0{i + 1}"
        draw.text((box_x1 + 28, py + 20), num_text, font=num_font, fill=point_accent, anchor="la")

        # 要点文字
        text_x = box_x1 + 90
        text_y = py + 20
        for line in lines:
            draw.text((text_x, text_y), line, font=point_font, fill=point_text_color, anchor="la")
            text_y += line_height

    # ── 5. 底部标签 ──
    if tags:
        tag_font = _load_font(26)
        tag_color = colors["accent_color"]
        if len(tag_color) == 3:
            tag_color = tag_color + (200,)

        tag_x = 100
        tag_y = CARD_HEIGHT - 240
        tag_padding = 16
        tag_gap = 12

        for tag in tags[:4]:  # 最多显示4个标签
            tag_bbox = draw.textbbox((0, 0), f"# {tag}", font=tag_font)
            tag_w = tag_bbox[2] - tag_bbox[0] + tag_padding * 2
            tag_h = tag_bbox[3] - tag_bbox[1] + tag_padding

            _draw_rounded_rect(
                draw,
                (tag_x, tag_y, tag_x + tag_w, tag_y + tag_h + 8),
                radius=20,
                fill=tag_color[:3] + (40,),
                outline=tag_color,
                width=1,
            )
            draw.text(
                (tag_x + tag_padding, tag_y + 4),
                f"# {tag}",
                font=tag_font,
                fill=tag_color,
                anchor="la",
            )
            tag_x += tag_w + tag_gap

    # ── 6. 底部总结 ──
    summary_font = _load_font(34)
    summary_text_color = colors["summary_text"]
    if len(summary_text_color) == 3:
        summary_text_color = summary_text_color + (255,)

    summary_bg_color = colors["summary_bg"]
    if len(summary_bg_color) == 3:
        summary_bg_color = summary_bg_color + (255,)

    summary_border = colors["summary_border"]
    if len(summary_border) == 3:
        summary_border = summary_border + (255,)

    # 总结文字换行
    summary_lines = _wrap_text(draw, summary, summary_font, box_max_w)
    summary_line_h = 46
    summary_box_h = max(80, len(summary_lines) * summary_line_h + 40)
    summary_y = CARD_HEIGHT - 180 - summary_box_h

    _draw_rounded_rect(
        draw,
        (box_x1, summary_y, box_x2, summary_y + summary_box_h),
        radius=16,
        fill=summary_bg_color,
        outline=summary_border,
        width=2,
    )

    # 左侧装饰竖条
    _draw_rounded_rect(
        draw,
        (box_x1 + 8, summary_y + 12, box_x1 + 12, summary_y + summary_box_h - 12),
        radius=4,
        fill=colors["accent_color"] + (200,) if len(colors["accent_color"]) == 3 else colors["accent_color"],
    )

    # 总结文字
    s_text_x = box_x1 + 28
    s_text_y = summary_y + 20
    for line in summary_lines:
        draw.text((s_text_x, s_text_y), line, font=summary_font, fill=summary_text_color, anchor="la")
        s_text_y += summary_line_h

    # ── 合成最终图片 ──
    bg = bg.convert("RGBA")
    result = Image.alpha_composite(bg, canvas)

    return result.convert("RGB")


def knowledge_card_gen_node(
    state: KnowledgeCardGenInput,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> KnowledgeCardGenOutput:
    """
    title: 生成知识卡片
    desc: 用AI生成背景图 + Pillow渲染文字，生成1080x1920知识卡片
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

    # ── 生成背景图 ──
    try:
        from coze_coding_dev_sdk import ImageGenerationClient

        bg_prompt = STYLE_BG_PROMPTS.get(style, STYLE_BG_PROMPTS["dark-tech"])
        image_model = os.getenv("IMAGE_GEN_MODEL") or "doubao-seedream-5-0-260128"

        img_client = ImageGenerationClient()
        response = img_client.generate(
            prompt=bg_prompt,
            model=image_model,
            size="1440x2560",
            batch_size=1,
        )

        # 解析返回的图片URL
        bg_url = None
        if hasattr(response, "image_urls") and response.image_urls:
            bg_url = response.image_urls[0]
        elif isinstance(response, dict):
            urls = response.get("image_urls") or response.get("urls") or response.get("data", [])
            if isinstance(urls, list) and urls:
                bg_url = urls[0] if isinstance(urls[0], str) else urls[0].get("url")

        if not bg_url:
            raise ValueError("背景图生成失败：未返回图片URL")

        logger.info(f"背景图已生成: {bg_url[:80]}...")

        # 下载背景图
        resp = requests.get(bg_url, timeout=60)
        resp.raise_for_status()
        bg_img = Image.open(io.BytesIO(resp.content))

    except Exception as e:
        logger.warning(f"背景图生成失败，使用纯色背景: {e}")
        bg_img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (20, 25, 50))

    # ── Pillow 渲染卡片 ──
    try:
        card_img = _render_card(
            background=bg_img,
            title=title,
            key_points=key_points,
            summary=summary,
            tags=tags,
            style=style,
        )

        # 保存到临时文件
        tmp_path = os.path.join(tempfile.gettempdir(), f"knowledge_card_{int(time.time() * 1000)}.png")
        card_img.save(tmp_path, "PNG", optimize=True)
        logger.info(f"卡片已渲染: {tmp_path}")

    except Exception as e:
        logger.error(f"卡片渲染失败: {e}")
        return KnowledgeCardGenOutput(
            card_image_url="",
            card_content=card_content,
            error=f"卡片渲染失败: {e}",
        )

    # ── 上传到对象存储 ──
    try:
        from coze_coding_dev_sdk import S3SyncStorage

        storage = S3SyncStorage()

        with open(tmp_path, "rb") as f:
            file_data = f.read()

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

        # 清理临时文件
        try:
            os.remove(tmp_path)
        except Exception:
            pass

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