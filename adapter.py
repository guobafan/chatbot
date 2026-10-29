
# -----------------------------------
# 适配流式输出时思考与回答内容的展示
# -----------------------------------
from typing import Iterable
import streamlit as st


class StreamlitAdapter:
    reasoning_content = '' # 完整思考内容
    content = '' # 完整回答内容
    _reasoning_el = None # 显示完整思考内容的元素
    _content_el = None # 显示完整回答内容的元素

    def render(self, chunks: Iterable[tuple[str, str]]):
        for _content, _reasoning_content in chunks:
            if _reasoning_content:
                self._render_reasoning(_reasoning_content)
            if _content:
                self._render_content(_content)
        return self.content, self.reasoning_content

    def _render_reasoning(self, text: str):
        """渲染一个块中新增的思考内容文本"""
        if self._reasoning_el is None:
            with st.expander('深度思考: ', expanded=True):
                self._reasoning_el = st.empty()
        self.reasoning_content += text
        self._reasoning_el.markdown(self.reasoning_content)

    def _render_content(self, text: str):
        """渲染一个块中新增的回答内容文本"""
        if self._content_el is None:
            self._content_el = st.empty()
        self.content += text
        self._content_el.markdown(self.content)
