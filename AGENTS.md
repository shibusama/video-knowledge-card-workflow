## 项目概述
- **名称**: 视频内容分析与总结图片生成工作流
- **功能**: 输入视频链接，自动分析视频内容提取核心信息，并生成高质量的总结图片

## 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| video_analysis | `nodes/video_analysis_node.py` | agent | 使用多模态大模型分析视频内容，提取核心信息（主要观点、关键画面、重要标题等） | - | `config/video_analysis_llm_cfg.json` |
| summary_image_gen | `nodes/summary_image_gen_node.py` | task | 根据视频分析结果生成高质量的总结图片 | - | `config/summary_image_gen_cfg.json` |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 子图清单
无

## 技能使用
- 节点`video_analysis`使用大语言模型技能（多模态视频理解）
- 节点`summary_image_gen`使用图片生成技能

## 工作流结构
```
输入(视频链接) → video_analysis(视频内容分析) → summary_image_gen(总结图片生成) → 输出(总结图片URL)
```
