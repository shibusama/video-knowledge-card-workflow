from typing import Optional, List
from pydantic import BaseModel, Field
from utils.file.file import File


class GlobalState(BaseModel):
    """全局状态定义"""
    video_url: File = Field(..., description="输入的视频文件/链接")
    style: str = Field(default="dark-tech", description="知识卡片艺术风格：dark-tech(深色科技)/pop(波普)/cyber(赛博)/vaporwave(蒸汽波)/glassmorphism(玻璃拟态)/bauhaus(包豪斯)")
    card_content: dict = Field(default={}, description="从视频中提炼的知识卡片结构化内容")
    card_image_url: str = Field(default="", description="生成的知识卡片图片URL")
    manual_content: Optional[dict] = Field(default=None, description="手动输入的视频内容描述（可选）")


class GraphInput(BaseModel):
    """工作流的输入"""
    video_url: File = Field(..., description="输入的视频文件/链接（支持抖音链接和直接视频URL）")
    style: str = Field(default="dark-tech", description="知识卡片艺术风格：dark-tech(深色科技)/pop(波普)/cyber(赛博)/vaporwave(蒸汽波)/glassmorphism(玻璃拟态)/bauhaus(包豪斯)")
    manual_content: Optional[dict] = Field(default=None, description="手动输入的视频内容描述（可选），格式：{\"title\":\"...\",\"key_points\":[...],\"summary\":\"...\",\"tags\":[...]}")


class GraphOutput(BaseModel):
    """工作流的输出"""
    card_image_url: str = Field(default="", description="生成的知识卡片图片URL")
    card_content: dict = Field(default={}, description="知识卡片结构化内容")
    error: Optional[str] = Field(default=None, description="如果URL无法解析，返回错误信息")


class VideoAnalysisInput(BaseModel):
    """视频内容分析节点的输入"""
    video_url: File = Field(..., description="输入的视频文件/链接")
    manual_content: Optional[dict] = Field(default=None, description="手动输入的视频内容描述")


class VideoAnalysisOutput(BaseModel):
    """视频内容分析节点的输出"""
    card_content: dict = Field(default={}, description="从视频中提炼的知识卡片结构化内容，包含title/key_points/summary等字段")
    error: Optional[str] = Field(default=None, description="如果URL无法解析，返回错误信息")


class KnowledgeCardGenInput(BaseModel):
    """知识卡片生成节点的输入"""
    card_content: dict = Field(default={}, description="知识卡片结构化内容")
    style: str = Field(default="dark-tech", description="知识卡片艺术风格")
    error: Optional[str] = Field(default=None, description="上游传递的错误信息，有值时跳过卡片生成")


class KnowledgeCardGenOutput(BaseModel):
    """知识卡片生成节点的输出"""
    card_image_url: str = Field(default="", description="生成的知识卡片图片URL")
    error: Optional[str] = Field(default=None, description="透传上游的错误信息")
