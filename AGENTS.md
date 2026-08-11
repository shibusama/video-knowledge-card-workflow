## 项目概述
- **名称**: 视频知识卡片生成工作流
- **功能**: 输入视频链接，自动分析视频内容提炼核心知识，采用「AI分析内容 + Seedream 5.0 直接生图」方案生成高质量知识卡片图片

## 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| video_analysis | `nodes/video_analysis_node.py` | agent | 使用多模态大模型分析视频内容，提炼结构化知识卡片文案（标题、要点、总结）。支持抖音链接（页面文本提取）与视频号链接（元宝解析直链/回退页面文本） | 抖音链接走 `_is_douyin_url` 分支；视频号链接走 `is_sph_url`（元宝）分支；其余按普通视频URL多模态分析。**URL不可解析时直接返回错误，不生成卡片** | `config/video_analysis_llm_cfg.json` |
| knowledge_card_gen | `nodes/knowledge_card_gen_node.py` | task | **直接用Seedream 5.0生成完整知识卡片**（含文字+背景+排版）。提示词动态拼接结构化文案+风格描述+布局模板。**检测到上游有error时跳过生成** | 布局5种轮换、风格6种随机 | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 子图清单
无

## 技能使用
- 节点`video_analysis`使用大语言模型技能（多模态视频理解）
- 节点`knowledge_card_gen`使用图片生成技能（Seedream 5.0直接生图）

## 支持风格
| 风格ID | 名称 | 适用场景 | 变体数 |
|--------|------|---------|-------|
| dark-tech | 深色科技 | AI/科技/效率类内容 | 2种变体 |
| pop | 波普 | 年轻、吸睛、趣味内容 | 2种变体 |
| cyber | 赛博酷炫 | 技术、硬核内容 | 3种变体 |
| vaporwave | 蒸汽波 | 怀旧、音乐、潮流内容 | 2种变体 |
| glassmorphism | 玻璃拟态 | 通透高级感 | 2种变体 |
| bauhaus | 包豪斯 | 设计、教育、技术 | 2种变体 |
| **random** | **随机** | 不指定风格时自动随机选 | 全部 |

## 工作流结构
```
输入(视频/抖音/视频号链接 + 风格选择) → video_analysis(视频内容分析) → knowledge_card_gen(Seedream 5.0直接生图) → 输出(卡片图片URL)
```

## 核心方法论
- **内容用AI提炼**：多模态大模型分析视频，提取结构化文案
- **卡片用AI直接生成**：Seedream 5.0根据提示词一次性生成完整卡片（含文字+背景+排版）
- **布局轮换**：5种不同布局模板，每次随机选
- **风格轮换**：6种风格 × 每种2-3个变体描述，每次随机组合

## URL可解析性检测
- 工作流运行时先检测URL是否可解析
- **抖音链接**：尝试获取页面内容，拿不到返回错误
- **视频号链接**：检查`HY_TOKEN`是否配置，未配置返回错误
- **普通链接**：发HEAD请求检查可达性，404/无法连接返回错误
- 不可解析时直接返回`error`字段，不浪费算力生成卡片

## 环境变量支持
| 环境变量 | 用途 | 默认值 |
|---------|------|--------|
| `VIDEO_ANALYSIS_MODEL` | 覆盖视频分析模型 | `doubao-seed-2-0-pro-260215` |
| `IMAGE_GEN_MODEL` | 覆盖图片生成模型 | `doubao-seedream-5-0-260128` |
| `HY_TOKEN` | 腾讯元宝cookie，用于视频号解析 | 无（必填才能解析视频号） |

## API接口（部署后）
| 接口 | 方法 | 说明 |
|------|------|------|
| `/run` | POST | 同步运行，返回卡片图片URL |
| `/stream_run` | POST | 流式运行，实时返回节点中间结果 |
| `/async_run` | POST | 异步运行，返回task_id |
| `/task/{task_id}` | GET | 查询异步任务结果 |
| `/graph_parameter` | GET | 获取工作流入参结构 |
| `/health` | GET | 健康检查 |

## 视频号（微信频道）链接解析
- **能力**：输入 `weixin.qq.com/sph` 或 `channels.weixin.qq.com` 分享链接，自动解析出可播放直链再送入多模态分析。
- **实现**：`src/utils/wechat_sph.py`，两步纯HTTP：分享链接 → 腾讯元宝换取 exportId/token → 微信频道换取 videoUrl。仅用标准库 urllib，无第三方依赖。
- **依赖环境变量**：`HY_TOKEN`（腾讯元宝 cookie，浏览器登录元宝后 F12 获取）。未配置时解析抛异常，节点回退到页面文本提取。
- **来源**：移植自 `wx_channels_download/internal/api/sph/worker.js`，与 `taixing-ideabox` 的 `_parse_wechat_yuanbao` 逻辑一致。

## 部署注意事项
部署到 Coze 平台时，**无需任何构建脚本**，零依赖，直接部署即可运行。

（卡通用 Pillow 纯 Python 渲染，无需 Playwright/Chromium，部署环境无网络权限也能正常运行）
