# SpeakBuddy 云端部署 · 2026-11-08

Web UI：
https://sejf11jm5l5120920cjjc.apigateway-ap-southeast-1.apigw-byteplus.com/

## 运行配置

| 项目 | 配置 |
| --- | --- |
| 区域 | ap-southeast-1 |
| 函数名称 / ID | speakbuddy-20261108 / fewtji66 |
| 当前已发布 revision | 3，100% 流量 |
| veFaaS Runtime | native/v1 |
| 依赖构建平台 | Linux amd64，Python 3.9 |
| CPU / 内存 | 1 vCPU / 2048 MB |
| 最少 / 最多实例 | 1 / 1 |
| Uvicorn workers | 1 |
| 每实例最大请求并发 | 32 |
| 函数 / 网关请求超时 | 120 秒 / 120000 毫秒 |
| 初始化超时 | 60 秒 |
| 存储 | TOS 私有桶 alex-demo |
| 默认音色 | Candice |
| 网关 Service ID | sejf11jm5l5120920cjjc |

启动命令：

```sh
./run_vefaas.sh
```

脚本执行：

```sh
python3 -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${_FAAS_RUNTIME_PORT:-8000}" \
  --workers 1 \
  --timeout-graceful-shutdown "${_FAAS_FUNC_TIMEOUT:-120}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
```

脚本设置 `PYTHONDONTWRITEBYTECODE=1`，不会在运行时生成源码缓存。

## 环境变量清单

真实密钥及模型 endpoint ID 只存在于权限为 0600 的本地 `.env` 和云端函数环境变量中。以下清单不包含这些值。

| 环境变量 | 说明 / 非敏感配置 |
| --- | --- |
| APP_ENV | production |
| APP_BASE_URL | 上面的 HTTPS Web UI 地址 |
| DATABASE_URL | sqlite:////tmp/speakbuddy/speakbuddy.db |
| LOCAL_DATA_DIR | /tmp/speakbuddy |
| MOCK_AI | false |
| SESSION_SECRET | 从 `.env` 注入的独立随机签名密钥 |
| BYTEPLUS_AK | 从 `.env` 注入 |
| BYTEPLUS_SK | 从 `.env` 注入 |
| STORAGE_BACKEND | tos |
| TOS_REGION | ap-southeast-1 |
| TOS_BUCKET | alex-demo |
| TOS_ENDPOINT | https://tos-ap-southeast-1.bytepluses.com |
| MODELARK_API_KEY | 从 `.env` 注入 |
| MODELARK_BASE_URL | https://ark.ap-southeast.bytepluses.com/api/v3 |
| MAIN_AGENT_ENDPOINT | deepseek-v4.1-flash-off 的 endpoint，从 `.env` 注入 |
| SCRIPT_ENDPOINT | 同主模型，从 `.env` 注入 |
| VIDEO_REVIEW_ENDPOINT | seed-2.1-turbo-off 的 endpoint，从 `.env` 注入 |
| VIDEO_ENDPOINT | seedance-2.5-off 的 endpoint，从 `.env` 注入 |
| IMAGE_ENDPOINT | seedream-5.0-flash 的 endpoint，从 `.env` 注入 |
| SPEECH_APPID | 从 `.env` 注入 |
| SPEECH_API_KEY | 从 `.env` 注入 |
| BYTEPLUS_ASR_URL | https://voice.ap-southeast-1.bytepluses.com/api/v3/auc/bigmodel |
| BYTEPLUS_ASR_RESOURCE_ID | volc.seedasr.auc |
| BYTEPLUS_ASR_STREAM_URL | wss://voice.ap-southeast-1.bytepluses.com/api/v3/sauc/bigmodel_async |
| BYTEPLUS_ASR_STREAM_RESOURCE_ID | volc.seedasr.sauc.duration |
| BYTEPLUS_TTS_URL | https://voice.ap-southeast-1.bytepluses.com/api/v3/tts/unidirectional |
| BYTEPLUS_TTS_RESOURCE_ID | seed-tts-1.0 |
| BYTEPLUS_TTS_VOICE | en_female_candice_emo_v2_mars_bigtts |

本地 `.env` 的环境和数据库路径保留本地配置；发布时覆写为上述云端值。采用新的 `speakbuddy-nov08` bp profile；旧账户和其他项目的云资源未修改。

## 部署与依赖

```sh
sh scripts/build_vefaas.sh
```

构建脚本在 Linux amd64 / Python 3.9 容器中安装 `requirements-vefaas.txt`，把运行库与 `app`、`plans`、启动脚本打入 `.vefaas/speakbuddy-vefaas.zip`。

直接依赖：FastAPI 0.115.12、Uvicorn 0.34.2、WebSockets 15.0.1、Jinja2 3.1.6、SQLModel 0.0.24、pydantic-settings 2.9.1、eval-type-backport 0.4.0、python-multipart 0.0.20、HTTPX 0.28.1、OpenAI SDK 1.82.0、TOS SDK 2.8.7、qrcode 8.2。Linux 原生扩展及导入、数据库初始化、首页与健康检查均已验证。

使用 `bp vefaas CreateFunction` 创建函数；首次创建从私有 TOS 对象载入代码。后续使用 `GetCodeUploadAddress`、上传代码、`CodeUploadCallback`、`Release` 发布新 revision。`bp apig CreateGatewayService`、`CreateUpstream` 和 `bp apig20221112 CreateRoute` 绑定 HTTPS 网关，路径 `/` 按前缀匹配，禁用网关重试，支持 HTTP 和 WebSocket。

部署包不含 `.env`、`docs`、`tests`、`test`、Git 元数据或 Python 缓存。发布前逐文件检查真实 AK、SK、API key、会话密钥、模型 endpoint 字节，匹配即停止发布。本说明文件也不进入部署包。

检查发布及实例：

```sh
bp vefaas GetReleaseStatus --FunctionId fewtji66 \
  --profile speakbuddy-nov08 --region ap-southeast-1
bp vefaas GetFunctionResource --FunctionId fewtji66 \
  --profile speakbuddy-nov08 --region ap-southeast-1
bp vefaas ListFunctionInstances --FunctionId fewtji66 \
  --profile speakbuddy-nov08 --region ap-southeast-1
```

## 隔离与运行边界

- 匿名访客使用独立的 HttpOnly Cookie；账户采用数据库内的随机身份标识，防止实例重建后整数 ID 重用导致身份串用。
- 每个练习窗口有独立 `conversation_id`，提交、完成和提前结束仅影响该对话。已结束对话不接受延迟到达的模型结果。
- 上传音频使用用户目录与 UUID 文件名；音频代理和 ASR 校验归属，其他访客不能读取录音或评分私有主题。
- TOS 私有对象的签名 URL 仅在服务端用于取音频及 ASR；浏览器收到 `/api/audio/...`，不会收到签名中的 AK 标识。
- 模型请求使用独立异步客户端和有限超时；数据库写入为短事务并串行保护积分更新。内容准备和同步 SDK 放在线程中，ASR 断连会取消并回收连接任务；HTTP 和 TOS 客户端显式关闭。
- 全局每日题库可共享，用户题目副本和练习记录独立。内容生成锁按用户分配并自动回收；内容锁等待超过 20 秒返回可重试的 503，不无限占用网关请求。

`MinInstance=MaxInstance=1` 是稳定运行配置。veFaaS 滚动发布可能临时保留旧实例或启动实例，必须等旧实例回收后再确认总实例数；发布过程不能保证物理实例始终只有一个。WebSocket 连接和 SQLite 数据位于实例内，发布、重建或故障切换会结束连接并可能丢失本地账户及练习记录。TOS 音频对象独立持久保存。需要跨重建保留账户和进度时，应改用外部数据库；当前配置不支持任意扩容为多实例。

## 验证

36 项本地回归测试、Ruff 和 Linux Python 3.9 打包应用启动检查通过。额外验证了多访客、多窗口同时提交、积分一致性、窗口独立结束、路径遍历拒绝和旧实例身份拒绝。

云端验证包括首页及七个功能页面、三路真实模型并发、对话独立完成、Candice 流式 TTS、TOS 上传、文件 ASR、WebSocket ASR、跨用户主题及音频拒绝，以及模型执行期间的健康响应。浏览器通过实际点击进入 Today's Quest、播放语音和页面导航检查。

最终实测：三路模型并发用时 3.37 秒，期间健康检查最大延迟 0.069 秒，流式 TTS 返回 21165 字节真实音频。浏览器确认 Candice 默认选中、`practice.js?v=9` 已加载且无横向溢出。云端环境变量中的 15 项凭据、模型与存储配置逐项核对通过，未输出真实值。

最终 `GetReleaseStatus` 为 `done`，stable revision 为 3；`GetFunctionResource` 为 `MinInstance=1 / MaxInstance=1`；`ListFunctionInstances` 仅返回 1 个 `Ready` 的预留实例。
