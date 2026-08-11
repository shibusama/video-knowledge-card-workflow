## 项目概述
- **名称**: 视频知识卡片生成工作流
- **功能**: 输入视频链接，自动分析视频内容提炼核心知识，采用「AI生成风格背景 + HTML渲染文字」混合方案生成高质量知识卡片图片

## 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| video_analysis | `nodes/video_analysis_node.py` | agent | 使用多模态大模型分析视频内容，提炼结构化知识卡片文案（标题、要点、总结）。支持抖音链接（Playwright抓流/回退页面文本）与视频号链接（元宝解析直链/回退页面文本） | 抖音链接走 `_is_douyin_url` 分支；视频号链接走 `is_sph_url`（元宝）分支；其余按普通视频URL多模态分析 | `config/video_analysis_llm_cfg.json` |
| knowledge_card_gen | `nodes/knowledge_card_gen_node.py` | task | 混合方案生成知识卡片：AI生成风格背景 + HTML/CSS叠字 + Playwright截图 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 子图清单
无

## 技能使用
- 节点`video_analysis`使用大语言模型技能（多模态视频理解）
- 节点`knowledge_card_gen`使用图片生成技能（Seedream生成风格背景）

## 支持风格
| 风格ID | 名称 | 适用场景 |
|--------|------|---------|
| dark-tech | 深色科技 | AI/科技/效率类内容（默认） |
| pop | 波普 | 年轻、吸睛、趣味内容 |
| cyber | 赛博酷炫 | 技术、硬核内容 |
| vaporwave | 蒸汽波 | 怀旧、音乐、潮流内容 |
| glassmorphism | 玻璃拟态 | 通透高级感 |
| bauhaus | 包豪斯 | 设计、教育、技术 |

## 工作流结构
```
输入(视频/抖音/视频号链接 + 风格选择) → video_analysis(视频内容分析) → knowledge_card_gen(知识卡片生成) → 输出(卡片图片URL)
```

## 核心方法论
- **内容用AI提炼**：多模态大模型分析视频，提取结构化文案
- **文字用HTML渲染**：保证文字100%准确，无AI幻觉
- **背景用AI生图**：Seedream生成风格化背景，提升视觉效果

## 视频号（微信频道）链接解析
- **能力**：输入 `weixin.qq.com/sph` 或 `channels.weixin.qq.com` 分享链接，自动解析出可播放直链再送入多模态分析。
- **实现**：`src/utils/wechat_sph.py`，两步纯HTTP：分享链接 → 腾讯元宝换取 exportId/token → 微信频道换取 videoUrl。仅用标准库 urllib，无第三方依赖。
- **依赖环境变量**：`HY_TOKEN`（腾讯元宝 cookie，浏览器登录元宝后 F12 获取）。未配置时解析抛异常，节点回退到页面文本提取。
- **来源**：移植自 `wx_channels_download/internal/api/sph/worker.js`，与 `taixing-ideabox` 的 `_parse_wechat_yuanbao` 逻辑一致。
