# 项目结构说明

# 本地运行
## 运行流程
bash scripts/local_run.sh -m flow

## 运行节点
bash scripts/local_run.sh -m node -n node_name

# 启动HTTP服务
bash scripts/http_run.sh -m http -p 5000

# 视频号链接解析
分析节点支持视频号（微信频道）分享链接（`weixin.qq.com/sph` / `channels.weixin.qq.com`）。
解析逻辑见 `src/utils/wechat_sph.py`，通过腾讯元宝两步HTTP换取直链后多模态分析。

依赖环境变量 `HY_TOKEN`（腾讯元宝 cookie，登录元宝后 F12 获取）：
```bash
export HY_TOKEN="your_yuanbao_cookie"
```
未配置时解析失败，节点会回退到页面文本提取。

