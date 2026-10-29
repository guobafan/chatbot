# 🤖 智能聊天机器人（day20）

Streamlit + OpenAI 兼容接口的大模型小应用：多轮对话、人设切换、流式输出、历史截断策略、意图识别、工单结构化。

## 目录

| 文件 | 作用 |
|---|---|
| `app.py` | 页面入口（Streamlit Cloud 的 Main file path 填它） |
| `llm.py` | OpenAI 客户端封装：`completion` / `stream` |
| `adapter.py` | 流式输出时「思考过程 + 回答」的分块渲染 |
| `prompts.py` | 人设与意图识别提示词 |
| `truncation.py` | 四种历史截断策略 |
| `schema.py` | Pydantic 校验 + JSON 容错解析 |

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

API 配置二选一：

1. 页面左侧栏直接填 `BASE_URL` / `API_KEY` / `MODEL_NAME`；
2. 复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml` 填好（或用 `.env` 里的
   `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `MODEL`）。

## 部署到 Streamlit Community Cloud

1. 推到 GitHub（公开仓库）；
2. share.streamlit.io → **New app** → 选仓库 / 分支 / `app.py`；
3. Settings → **Secrets** 里填 `BASE_URL`、`API_KEY`、`MODEL_NAME`；
4. 部署完成后地址是 `https://<app 名>.streamlit.app`。

`.env` 和 `.streamlit/secrets.toml` 已在 `.gitignore` 里，不会进仓库。
