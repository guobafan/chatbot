
import os

import streamlit as st
from llm import completion, stream, create_client
from adapter import StreamlitAdapter
from prompts import PERSONA, build_intent_messages, INTENT_DEMOS
from truncation import TRUNC_OPTIONS, build_messages
from schema import parse_json, Ticket


def _secret(name: str, default: str = '') -> str:
    """读配置：云端 Secrets 优先，其次本地 .env / 环境变量，最后用默认值。"""
    try:
        value = st.secrets.get(name, '')
    except Exception:  # 本地没有 .streamlit/secrets.toml 时读取会报错
        value = ''
    return str(value) or os.getenv(name, '') or default


# system系统角色（人设）
PERSONA_KEYS = list(PERSONA.keys())
# 所有截断策略名称
TRUNC_KEYS = list(TRUNC_OPTIONS.keys())
# 不同意图识别后显示的颜色
INTENT_COLORS = {'order': 'green', 'return': 'red', 'complain': 'blue'}

# 常用服务商：选一个会自动填好 BASE_URL 和模型名，访客只需要贴自己的 Key
PROVIDERS = {
    '魔搭 ModelScope（每天 2000 次免费）': ('https://api-inference.modelscope.cn/v1', 'deepseek-ai/DeepSeek-V4-Pro'),
    '阿里百炼 DashScope': ('https://dashscope.aliyuncs.com/compatible-mode/v1', 'deepseek-v4-flash-0731'),
    'DeepSeek 官方': ('https://api.deepseek.com/v1', 'deepseek-chat'),
    '自定义': ('', ''),
}


def apply_provider():
    """切换服务商时，把 BASE_URL 和模型名一起换掉（Key 不自动清空）。"""
    base_url, model_name = PROVIDERS[st.session_state.provider]
    st.session_state.base_url = base_url
    st.session_state.model_name = model_name


def init_state():
    """初始化 session_state 中保存的状态数据"""
    default_state = {
        'history': [],
        'is_stream': False,
        'temperature': 0.7,
        'max_tokens': 5120,
        'thinking': False,
        'persona': 'coder',
        'trunc': 'none', # 截断策略
        'keep': 10, # 窗口大小轮数
        'budget': 1024, # token预算阈值上限
        'tab': '💬智能聊天',
        'provider': list(PROVIDERS)[0],
        'base_url': _secret('BASE_URL', PROVIDERS[list(PROVIDERS)[0]][0]),
        # Key 永远从空开始：谁用谁填自己的，站点不提供公共额度
        'api_key': '',
        'model_name': _secret('MODEL_NAME', PROVIDERS[list(PROVIDERS)[0]][1]),
    }
    # 将各状态数据的初始值保存到 st.session_state 中。
    # session_state 可在一次会话的多次 rerun 情况下共享状态数据
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

st.set_page_config('智能聊天机器人', page_icon='🤖', initial_sidebar_state='collapsed', layout='wide')
# ----------------------------------------------------------------
# 侧边栏
# ----------------------------------------------------------------
with st.sidebar:
    st.header('⚙️ 控制面板')
    st.markdown('**运行模式:** 🟢 真实大模型')
    st.caption('本应用不自带额度：填你自己的 API Key 才能聊天。')
    st.divider()
    st.selectbox(
        '服务商',
        options=list(PROVIDERS),
        key='provider',
        on_change=apply_provider,
        help='选好服务商会自动填 BASE_URL 和模型名，你只需要贴自己的 Key',
    )
    st.text_input('BASE_URL', key='base_url', placeholder='https://xxx/v1')
    st.text_input('API_KEY（你自己的）', key='api_key', type='password', placeholder='sk-... / ms-...')
    if not st.session_state.api_key:
        st.caption('⚠️ 没填 Key：三个功能都点不动。Key 只存在当前浏览器会话，不上传、不落盘。')
    st.text_input('MODEL_NAME', key='model_name', placeholder='模型名')
    st.divider()
    # 下拉选择框
    st.session_state.persona = st.selectbox('选择人设', options=PERSONA_KEYS, index=PERSONA_KEYS.index(st.session_state.persona))
    st.divider()
    # 复选框
    is_stream = st.checkbox('流式输出', value=st.session_state.is_stream)
    # 如果有修改流式输出的选择，则将修改后的值保存到 session_state 中
    st.session_state.is_stream = is_stream
    # 滑块
    temperature = st.slider('temperature', min_value=0.0, max_value=2.0, step=0.1, value=st.session_state.temperature)
    st.session_state.temperature = temperature
    max_tokens = st.slider('max_tokens', min_value=1024, max_value=65536, step=1024, value=st.session_state.max_tokens)
    st.session_state.max_tokens = max_tokens
    st.divider()
    # 截断策略
    st.session_state.trunc = st.selectbox('截断策略', options=TRUNC_KEYS, index=TRUNC_KEYS.index(st.session_state.trunc),
                 format_func=lambda key: TRUNC_OPTIONS[key])
    if st.session_state.trunc == 'turns':
        st.session_state.keep = st.number_input('轮数设置', min_value=6, max_value=20, step=1, value=st.session_state.keep)
    if st.session_state.trunc == 'tokens':
        st.session_state.budget = st.number_input('Token阈值', min_value=1000, max_value=3000, step=64, value=st.session_state.budget)

# 侧边栏渲染完再建客户端：刚填好的 BASE_URL / API_KEY 这次运行就能生效
model_name = st.session_state.model_name
if (bu := st.session_state.base_url) and (ak := st.session_state.api_key):
    client = create_client(base_url=bu, api_key=ak)
else:
    # 没有 Key 就不建客户端：页面只做提示，不偷偷用站长的额度
    client = None

# ----------------------------------------------------------------
# 页面主体
# ----------------------------------------------------------------
st.header('🤖 智能聊天机器人')
st.caption('大模型API与提示词工程')
if client is None:
    st.info('👈 先展开左侧「控制面板」（左上角 »），选服务商、贴上 **你自己的 API Key**。这个应用不提供公共额度。')
# 选项卡
tabs = st.tabs(['💬智能聊天', '🎯意图识别', '📋工单结构化'], on_change='rerun', key='tab')

with tabs[0]: # 智能聊天
    with st.container(horizontal=True, horizontal_alignment='distribute'):
        st.markdown('可实现**多轮对话**: 侧边切换人设、流式输出、截断策略')
        thinking = st.toggle('深度思考', value=st.session_state.thinking)
        st.session_state.thinking = thinking
    # 显示聊天对话历史
    with st.container(autoscroll=True):
        his = st.session_state.history
        for index in range(0, len(his), 2):
            st.chat_message('user').markdown(his[index]['content'])
            if index + 1 >= len(his): # 上一轮没答完（调用异常），跳过
                break
            ai_msg = his[index + 1]
            with st.chat_message('ai'):
                if rc := ai_msg.get('reasoning_content'):
                    with st.expander('深度思考:', expanded=False):
                        st.markdown(rc)
                st.markdown(ai_msg['content'])
        # 输入聊天问题
        message = ''
        if client is None:
            st.caption('（填上 API Key 后这里才会出现输入框）')
        elif st.session_state.tab == '💬智能聊天':
            with st.bottom:
                message = st.chat_input(placeholder='请输入您的问题，回车发送...')
    if message: # 有输入问题，则接入大语言模型进行解答
        # 将当前用户提问消息添加到历史记录中
        st.session_state.history.append({'role': 'user', 'content': message})
        # 界面中显示用户问题
        st.chat_message('user').write(message)
        content, reasoning_content = '', ''
        try:
            # 构建发送消息的列表
            msgs = build_messages(
                client,
                model_name,
                PERSONA[st.session_state.persona], # 系统角色提示词
                st.session_state.history, # 所有历史记录
                st.session_state.trunc, # 选择的截断策略
                st.session_state.keep, # 滑动窗口保留的数据轮数
                st.session_state.budget, # Token封顶阈值
            )
            if st.session_state.is_stream: # 流式输出
                chunks = stream(
                    messages=msgs,
                    model=model_name,
                    client=client,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens,
                    thinking=st.session_state.thinking,
                )
                # 后续数据处理
                with st.chat_message('ai'):
                    content, reasoning_content = StreamlitAdapter().render(chunks)
            else: # 非流式输出
                with st.spinner('思考中...'):
                    content, reasoning_content, total_tokens = completion(
                        messages=msgs,
                        model=model_name,
                        client=client,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                        thinking=st.session_state.thinking,
                    )
                # 显示结果
                with st.chat_message('ai'):
                    # 如果有开启思考模式，则显示思考过程内容
                    if st.session_state.thinking:
                        with st.expander('深度思考: ', expanded=True):
                            st.markdown(reasoning_content)
                    # 显示回答内容
                    st.markdown(content)
        except Exception as exc: # 鉴权失败/模型名写错/网络不通都在这里兜底，不整页红屏
            st.error(f'调用大模型失败：{type(exc).__name__}: {exc}')
        finally:
            # 回答完毕后，将 AI 助手的消息也保存到历史记录中
            if content:
                st.session_state.history.append({'role': 'assistant', 'content': content, 'reasoning_content': reasoning_content})

with tabs[1]: # 意图识别
    st.markdown('**意图识别**：用 `system` 约束＋少量示例，让模型只输出 `order / return / complain` 之一。')
    question = st.text_area('用户提问', value='我上周买的东西什么时候发货？', height=80)
    cols = st.columns(2) # 分两列
    with cols[0]: # 左边列
        if st.button('意图识别', type='primary', disabled=client is None):
            try:
                msgs = build_intent_messages(question)
                result = completion(
                    msgs,
                    model=model_name,
                    client=client,
                    temperature=0,
                )
                label = (result[0] or '').strip().lower()
                color = INTENT_COLORS.get(label, 'gray') # 模型没按约定输出时用灰色，不抛 KeyError
                st.markdown(
                    f'分类结果: <span style="color: {color}; font-size: 24px">{label or "(空)"}</span>',
                    unsafe_allow_html=True,
                )
            except Exception as exc:
                st.error(f'意图识别失败：{type(exc).__name__}: {exc}')
    with cols[1]: # 右边列
        st.markdown('使用的 `Few-shot` 示例: ')
        for q, a in INTENT_DEMOS:
            st.markdown(f'- 「{q}」 -> `{a}`')

with tabs[2]: # 工单结构化处理
    st.markdown('**结构化输出**：用 `response_format=json_object` 从协议层保证合法JSON，再用 `Pydantic` 做“最后一公里”校验。')
    cols = st.columns(2) # 2列布局
    with cols[0]: # 左边列
        st.subheader('工单抽取')
        txt = st.text_area('自然语言工单', value='下午3点在会议室2319开会，参加人员有: 小明，小红，小刚，老王，老李', height=80)
        if st.button('解析', key='btn_ticket', disabled=client is None):
            try:
                sys_message = {
                    'role': 'system',
                    'content': '你是工单抽取助手，要求抽取为严格的 JSON 格式，包括 intent(意图字符串)、time(时间字符串)、people(人数整数)、position(地点字符串)'
                }
                messages = [sys_message, {'role': 'user', 'content': txt}]
                # 接入大语言模型对话
                result = completion(
                    messages,
                    model=model_name,
                    client=client,
                    temperature=0,
                    response_format={'type': 'json_object'},
                )
                # 将回答内容（JSON）解析为 Python 值
                data = parse_json(result[0])
                if not isinstance(data, dict):
                    st.warning(f'模型返回的不是合法 JSON，原文：{result[0][:200]}')
                else:
                    data['people'] = '4'
                    # 利用 pydantic 进行校验
                    data = Ticket(**data) # Ticket(intent='', time='', people=1, position='')
                    st.text(data)
            except Exception as exc:
                st.error(f'工单解析失败：{type(exc).__name__}: {exc}')

    with cols[1]: # 右边列
        st.subheader('报销单')
        txt = st.text_area('报销文本: ', value='文本：餐费 120，打车 30，住宿 350，合计多少？', height=80)
        if st.button('解析', key='btn_cot', disabled=client is None):
            try:
                sys_message = {
                    'role': 'system',
                    'content': '从文本抽取字段并核对金额。输出严格 JSON: {"reasoning": str, "result": {"items": [str], "total": float}}',
                }
                messages = [
                    sys_message,
                    {'role': 'user', 'content': txt}
                ]
                with st.spinner('思考中...'):
                    result = completion(
                        messages,
                        model=model_name,
                        client=client,
                        temperature=0,
                        response_format={'type': 'json_object'},
                        thinking=False,
                    )
                    data = parse_json(result[0])
                    st.text(f'解析后: {data}')
                    st.text(f'响应数据: {result}')
            except Exception as exc:
                st.error(f'报销单解析失败：{type(exc).__name__}: {exc}')
