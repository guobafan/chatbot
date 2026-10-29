# 作者：小明
# 项目：day20
# 文件：llm.py
# 时间：2026/10/23 10:26
import os

from dotenv import load_dotenv
from openai import OpenAI
from typing import Iterable
from openai.types.chat import ChatCompletionMessageParam

load_dotenv()
# 默认模型名称：环境变量 > 默认值
default_model = os.getenv('MODEL_NAME') or os.getenv('MODEL') or 'deepseek-v4-flash-0731'
# 兜底 client：没有任何 key 时也不会在 import 阶段崩，真正的报错由页面上的 try/except 兜住
default_client = OpenAI(
    base_url=os.getenv('OPENAI_BASE_URL') or os.getenv('BASE_URL') or None,
    api_key=os.getenv('OPENAI_API_KEY') or os.getenv('API_KEY') or 'sk-placeholder',
)


def create_client(base_url: str, api_key: str):
    return OpenAI(base_url=base_url, api_key=api_key)


def completion(
    messages: Iterable[ChatCompletionMessageParam],
    model: str = default_model,
    client = default_client,
    *,
    temperature: float|int = 0.7,
    max_tokens: int = 4096,
    thinking: bool = False,
    **kwargs
):
    """非流式输出"""
    # 额外的主体参数: 通常是非标准OpenAI的参数，在extra_body中传递
    extra_body = {
        'enable_thinking': thinking, # 阿里云百炼供应商
        **kwargs,
    }
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )
    # 处理响应返回的结果对象
    msg = resp.choices[0].message
    return msg.content, getattr(msg, 'reasoning_content', '') if thinking else '', resp.usage.total_tokens


def stream(
    messages: Iterable[ChatCompletionMessageParam],
    model: str = default_model,
    client: OpenAI = default_client,
    *,
    temperature: float|int = 0.7,
    max_tokens: int = 4096,
    thinking: bool = False,
    **kwargs
):
    """流式输出"""
    # 额外的主体参数: 通常是非标准OpenAI的参数，在extra_body中传递
    extra_body = {
        'enable_thinking': thinking, # 阿里云百炼供应商
        **kwargs,
    }
    chunks = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        extra_body=extra_body,
    )
    # 循环迭代文档块
    for chunk in chunks:
        choices = chunk.choices
        choices = choices if len(choices) > 0 else [{}]
        delta = getattr(choices[0], 'delta', {})
        yield getattr(delta, 'content', ''), getattr(delta, 'reasoning_content', '') if thinking else ''
