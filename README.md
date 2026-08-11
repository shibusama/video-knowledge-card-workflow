# 项目结构说明

# 本地运行
## 运行流程
bash scripts/local_run.sh -m flow

## 运行节点
bash scripts/local_run.sh -m node -n node_name

# 启动HTTP服务
bash scripts/http_run.sh -m http -p 5000

# 部署说明

## 环境依赖（部署前必须安装）

工作流生成知识卡片时使用 **Playwright** 截图合成，部署环境需安装：

```bash
# 1. 安装 playwright Python 包（已在 pyproject.toml 中声明）
uv sync

# 2. 安装 Chromium 浏览器（部署时必须执行）
playwright install chromium
```

> **注意**：部署到 Coze 平台时，需要在**构建脚本**或**启动前脚本**中添加 `playwright install chromium`，否则卡片生成步骤会报错：
> ```
> Executable doesn't exist at /home/faas/.cache/ms-playwright/chromium_headless_shell-1161/chrome-linux/headless_shell
> ```

## 环境变量配置

| 环境变量 | 必填 | 用途 | 默认值 |
|---------|------|------|--------|
| `HY_TOKEN` | ✅ 解析视频号链接时必填 | 腾讯元宝 cookie，用于视频号链接解析 | 无 |
| `VIDEO_ANALYSIS_MODEL` | ❌ | 覆盖视频分析模型 | `doubao-seed-2-0-pro-260215` |
| `IMAGE_GEN_MODEL` | ❌ | 覆盖图片生成模型 | `doubao-seedream-5-0-260128` |

`HY_TOKEN` 获取方式：浏览器登录 [元宝](https://yuanbao.tencent.com) → F12 → 复制 cookie 中 `hy_token` 字段的值。

# 视频号链接解析
分析节点支持视频号（微信频道）分享链接（`weixin.qq.com/sph` / `channels.weixin.qq.com`）。
解析逻辑见 `src/utils/wechat_sph.py`，通过腾讯元宝两步HTTP换取直链后多模态分析。

依赖环境变量 `HY_TOKEN`（腾讯元宝 cookie，登录元宝后 F12 获取）：
```bash
export HY_TOKEN="your_yuanbao_cookie"
```
未配置时解析失败，节点会回退到页面文本提取。

