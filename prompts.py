

# 系统人设
PERSONA: dict = {
    "assistant": "你是一个友好、简洁的通用助手，回答准确、口语化。",
    "coder": "你是资深 Python 工程师，只给可运行代码与简短解释，不啰嗦。",
    "lawyer": "你是严谨的法律助理，只依据提供的事实回答，不得编造法条；不确定时明确说'未知'。",
    "translator": "你是中英互译助手，只做翻译并保持术语一致，不做解释。",
}

# 意图分类: 系统提示词
INTENT_SYSTEM = "你是客服意图分类器，仅输出 order/return/complain 之一，不要解释。"
# 小样本示例
INTENT_DEMOS = [
    ("我要查一下昨天下的订单", "order"), # (用户问题, AI回答)
    ("衣服小了想退货", "return"),
    ("你们的服务太差了", "complain"),
]

def build_intent_messages(text: str) -> list[dict[str, str]]:
    """构建意图分类的消息列表"""
    messages = [
        {'role': 'system', 'content': INTENT_SYSTEM},
    ]
    for q, a in INTENT_DEMOS:
        messages.append({'role': 'user', 'content': q})
        messages.append({'role': 'assistant', 'content': a})
    messages.append({'role': 'user', 'content': text})
    return messages
