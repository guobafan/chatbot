# 作者：小明
# 项目：day20
# 文件：truncation.py
# 时间：2026/10/23 16:23
from typing import List, Dict

# 截断策略
TRUNC_OPTIONS = {
    "none": "不截断（保留全部历史）",
    "turns": "轮数窗口（保留最近 N 轮）",
    "tokens": "Token 预算（从新到旧累加封顶）",
    "summary": "摘要压缩（旧对话压缩为摘要）",
}


# ------------------------------------------------------------------------------
# 历史记录截断策略
# ------------------------------------------------------------------------------
# 滑动窗口
def trim_by_turns(msgs: List[Dict], keep: int = 10) -> List[Dict]:
    """保留 system 消息 + 最近 keep 轮（每轮含 user+assistant 两条）。"""
    sys_msgs = [m for m in msgs if m.get("role") == "system"]
    dialog = [m for m in msgs if m.get("role") != "system"]
    return sys_msgs + dialog[-keep * 2:]


# token预算封顶
def trim_by_tokens(msgs: List[Dict], budget: int = 3000, enc=None) -> List[Dict]:
    """按 token 预算从新到旧保留；enc 为可选 tokenizer（如 tiktoken）。"""
    out, used = [], 0
    for m in reversed(msgs):
        content = m.get("content", "") or ""
        # 无编码器时按"字数//2"近似 token
        t = len(enc.encode(content)) if enc else len(content) // 2
        if used + t > budget:
            break
        out.insert(0, m)
        used += t
    return out


# 历史摘要压缩
def summarize_old(client, model, old_msgs: List[Dict], max_sentences: int = 3) -> str:
    """把旧对话压缩为若干句话要点（返回文本，供拼回 messages）。"""
    text = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in old_msgs)
    prompt = f"把以下对话压缩为最多 {max_sentences} 句话要点：\n{text}"
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}], temperature=0
    )
    return resp.choices[0].message.content or ""


def sliding_with_summary(client, model, msgs: List[Dict], keep: int = 12) -> List[Dict]:
    """组合策略：超过 keep 轮后，把更早的对话压成摘要，再拼上最近 keep 轮。

    注意 recent 必须按 keep 取尾部（原来写死 summary_threshold*2 会在 keep 很小时
    把最新几轮整段丢掉，导致模型看不到用户刚说的话）。
    """
    sys_msgs = [m for m in msgs if m.get("role") == "system"]
    dialog = [m for m in msgs if m.get("role") != "system"]
    if len(dialog) <= keep * 2:
        return msgs
    drop = dialog[:-keep * 2]
    recent = dialog[-keep * 2:]
    if not drop:
        return msgs
    summary = summarize_old(client, model, drop)
    summary_msg = {"role": "assistant", "content": f"[历史摘要] {summary}"}
    return sys_msgs + [summary_msg] + recent


def to_openai_messages(msgs: List[Dict]) -> List[Dict]:
    """只保留 role / content。

    history 里的 assistant 消息带着 reasoning_content，直接发给
    OpenAI 兼容接口属于未知字段，会被 400 拒绝，所以发请求前统一清洗。
    """
    return [{"role": m.get("role", "user"), "content": m.get("content") or ""} for m in msgs]


def build_messages(client, model, sys_prompt_text: str, history: list[dict], trunc_type: str, keep: int, budget: int):
    """基于截断策略构建消息列表"""
    # 根据系统人设，设置系统消息
    sys_message = {
        'role': 'system',
        'content': sys_prompt_text,
    }

    if trunc_type == 'turns': # 滑动窗口
        messages = trim_by_turns(history, keep)
    elif trunc_type == 'tokens': # Token封顶
        messages = trim_by_tokens(history, budget)
    elif trunc_type == 'summary':
        messages = sliding_with_summary(client, model, history, keep=keep)
    else:
        messages = history[:]

    return [sys_message] + to_openai_messages(messages)
