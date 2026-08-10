from typing import Optional, List
from pydantic import BaseModel, Field
from utils.file.file import File


class GlobalState(BaseModel):
    """全局状态定义"""
    video_url: File = Field(..., description="输入的视频文件/链接")
    analysis_result: str = Field(default="", description="视频内容分析结果")
    summary_image_url: str = Field(default="", description="生成的总结图片URL")


class GraphInput(BaseModel):
    """工作流的输入"""
    video_url: File = Field(..., description="输入的视频文件/链接")


class GraphOutput(BaseModel):
    """工作流的输出"""
    summary_image_url: str = Field(..., description="生成的总结图片URL")
    analysis_result: str = Field(default="", description="视频内容分析结果")


class VideoAnalysisInput(BaseModel):
    """视频内容分析节点的输入"""
    video_url: File = Field(..., description="输入的视频文件/链接")


class VideoAnalysisOutput(BaseModel):
    """视频内容分析节点的输出"""
    analysis_result: str = Field(..., description="视频内容分析结果，包含主要观点、关键画面、重要标题等核心信息")


class SummaryImageGenInput(BaseModel):
    """总结图片生成节点的输入"""
    analysis_result: str = Field(..., description="视频内容分析结果，包含核心信息摘要")


class SummaryImageGenOutput(BaseModel):
    """总结图片生成节点的输出"""
    summary_image_url: str = Field(..., description="生成的视频总结图片URL")
