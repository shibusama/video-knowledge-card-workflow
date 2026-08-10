from typing import Optional, List
from pydantic import BaseModel, Field
from utils.file.file import File


class GlobalState(BaseModel):
    """全局状态定义"""
    video_url: File = Field(..., description="输入的视频文件/链接")
    style: str = Field(default="dark-tech", description="知识卡片艺术风格：dark-tech(深色科技)/pop(波普)/cyber(赛博)/vaporwave(蒸汽波)/glassmorphism(玻璃拟态)/bauhaus(包豪斯)")
    card_content: dict = Field(default={}, description="从视频中提炼的知识卡片结构化内容")
    card_image_url: str = Field(default="", description="生成的知识卡片图片URL")


class GraphInput(BaseModel):
    """工作流的输入"""
    video_url: File = Field(..., description="输入的视频文件/链接")
    style: str = Field(default="dark-tech", description="知识卡片艺术风格：dark-tech(深色科技)/pop(波普)/cyber(赛博)/vaporwave(蒸汽波)/glassmorphism(玻璃拟态)/bauhaus(包豪斯)")


class GraphOutput(BaseModel):
    """工作流的输出"""
    card_image_url: str = Field(..., description="生成的知识卡片图片URL")
    card_content: dict = Field(default={}, description="知识卡片结构化内容")


class VideoAnalysisInput(BaseModel):
    """视频内容分析节点的输入"""
    video_url: File = Field(..., description="输入的视频文件/链接")


class VideoAnalysisOutput(BaseModel):
    """视频内容分析节点的输出"""
    card_content: dict = Field(..., description="从视频中提炼的知识卡片结构化内容，包含title/key_points/summary等字段")


class KnowledgeCardGenInput(BaseModel):
    """知识卡片生成节点的输入"""
    card_content: dict = Field(..., description="知识卡片结构化内容")
    style: str = Field(default="dark-tech", description="知识卡片艺术风格")


class KnowledgeCardGenOutput(BaseModel):
    """知识卡片生成节点的输出"""
    card_image_url: str = Field(..., description="生成的知识卡片图片URL")
