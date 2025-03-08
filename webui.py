import asyncio
import os
import sys

from dotenv import load_dotenv
import sounddevice as sd
import streamlit as st
import torch
from streamlit_autorefresh import st_autorefresh
from streamlit_chat import message
from streamlit_extras.let_it_rain import rain
from bilibiliconnection import BilibiliClient

from llmClient.llm_manager import LLMManager
from stt.voice_recognizer import VoiceRecognizer
from utils.utils import remove_emotion, get_image_as_data_uri

load_dotenv()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

torch.classes.__path__ = []

# 页面配置
st.set_page_config(
    page_title="Momotalk-天童爱丽丝",
    page_icon="🤖",
    layout="wide"
)

# 初始化session状态
if 'bili_connected' not in st.session_state:
    st.session_state.bili_connected = False
if 'bili_client' not in st.session_state:
    st.session_state.bili_client = None
# 初始化大模型实例
if "llm_manager" not in st.session_state:
    st.session_state.llm_manager = LLMManager()
# 初始化语音模块
if "voice_recognizer" not in st.session_state:
    st.session_state.voice_recognizer = VoiceRecognizer()
if "voice_prompt" not in st.session_state:
    st.session_state.voice_prompt = ""

# 彩效装饰（仅显示一次）
if "first_run" not in st.session_state:
    rain(emoji="✨", animation_length=1)
    st.session_state.first_run = True

# 侧边栏配置区域
with st.sidebar:
    st.header("⚙️ 系统设置")

    # 定义回调函数
    def llm_slider_changed():
        if st.session_state.llm_manager.llm is not None:
            st.session_state.llm_manager.llm.temperature = st.session_state.temperature
            st.session_state.llm_manager.llm.top_p = st.session_state.top_p
            st.session_state.llm_manager.llm.top_k = st.session_state.top_k
            st.session_state.llm_manager.llm.repetition_penalty = st.session_state.repetition_penalty
            st.session_state.llm_manager.llm.max_history = st.session_state.max_history


    # 大模型配置模块
    with st.expander("🔧 模型配置", expanded=True):
        model_type = st.selectbox(
            "大模型类型",
            ["本地模型"],
            index=0,
            help="选择大模型的部署类型（待开发）"
        )
        model_url = st.text_input(
            "大模型聊天地址",
            placeholder="请输入模型路径...",
            value="http://localhost:8000/v1/chat/completions",
            help="示例：http://localhost:8000/v1/chat/completions"
        )
        assistant_url = st.text_input(
            "大模型助手地址",
            placeholder="请输入模型路径...",
            value="http://localhost:8000/v1/assistant/completions",
            help="示例：http://localhost:8000/v1/assistant/completions"
        )
        temperature = st.slider(
            "temperature",
            0.00, 1.00, 0.94, 0.01,
            help="调整大模型温度参数",
            key="temperature",
            on_change=llm_slider_changed
        )
        top_p = st.slider(
            "top_p",
            0.00, 1.00, 0.6, 0.01,
            help="调整大模型top_p参数",
            key="top_p",
            on_change=llm_slider_changed
        )
        top_k = st.slider(
            "top_k",
            1, 100, 20, 1,
            help="调整大模型top_k参数",
            key="top_k",
            on_change=llm_slider_changed
        )
        repetition_penalty = st.slider(
            "repetition_penalty",
            1.0, 1.5, 1.1, 0.01,
            help="调整大模型重复惩罚参数",
            key="repetition_penalty",
            on_change=llm_slider_changed
        )
        max_history = st.slider(
            "最大历史",
            10, 100, 30, 1,
            help="调整大模型历史最大缓存长度",
            key="max_history",
            on_change=llm_slider_changed
        )
        # 动态按钮
        if st.session_state.llm_manager.llm is not None:
            # 断开按钮
            if st.button(
                    "🔴 关闭实例",
                    type="primary",
                    help="关闭大模型实例",
                    key="llm_close_btn"
            ):
                # 执行断开操作
                st.session_state.llm_manager.end_llm()
                st.rerun()
        else:
            # 连接按钮
            if st.button(
                    "🟢 开启实例",
                    type="primary",
                    help="创建大模型实例",
                    key="llm_open_btn"
            ):
                # 执行连接操作
                st.session_state.llm_manager.start_llm(
                    url=model_url,
                    url_assistant=assistant_url,
                    temperature=temperature,
                    top_p=top_p
                )
                st.rerun()

    # 定义回调函数
    def voice_slider_changed():
        if voice_enabled:
            st.session_state.voice_recognizer.silence_threshold = 1 / st.session_state.voice_sensitivity


    # 语音识别模块
    with st.expander("🎤 语音设置", expanded=True):
        # 设备选择
        devices = sd.query_devices()
        input_devices = [f"{i}: {d['name']}" for i, d in enumerate(devices)
                         if d['max_input_channels'] > 0]
        selected_device = st.selectbox("选择麦克风", input_devices, index=1)
        device_id = int(selected_device.split(":")[0])

        # 语音开关
        if voice_enabled := st.checkbox(
                "启用语音识别",
                value=False,
                help="开启语音输入功能"
        ):
            if not st.session_state.voice_recognizer.is_recording:
                st.session_state.voice_recognizer.start(
                    device_id=device_id, threshold=1 / st.session_state.voice_sensitivity)
        else:
            if st.session_state.voice_recognizer.is_recording:
                st.session_state.voice_recognizer.stop()
        voice_sensitivity = st.slider(
            "麦克风灵敏度",
            1, 100, 10,
            help="调整语音识别灵敏度",
            key="voice_sensitivity",
            on_change=voice_slider_changed
        )

    # B站连接模块
    with st.expander("📺 B站连接", expanded=True):
        bili_access_key_id = st.text_input(
            "ACCESS_KEY_ID",
            placeholder="输入ACCESS_KEY_ID",
            value=os.environ.get("ACCESS_KEY_ID"),
            help="bilibili直播间链接参数"
        )
        bili_access_key_secret = st.text_input(
            "ACCESS_KEY_SECRET",
            placeholder="输入ACCESS_KEY_SECRET",
            value=os.environ.get("ACCESS_KEY_SECRET"),
            help="bilibili直播间链接参数"
        )
        bili_app_id = st.text_input(
            "APP_ID",
            placeholder="输入APP_ID",
            value=os.environ.get("APP_ID"),
            help="bilibili直播间链接参数"
        )
        bili_room_auth_code = st.text_input(
            "ROOM_OWNER_AUTH_CODE",
            placeholder="输入ROOM_OWNER_AUTH_CODE",
            value=os.environ.get("ROOM_OWNER_AUTH_CODE"),
            help="bilibili直播间链接参数"
        )
        # 动态按钮
        if st.session_state.bili_connected:
            # 断开按钮
            if st.button(
                    "🔴 断开连接",
                    type="primary",
                    help="点击断开直播间连接",
                    key="disconnect_btn"
            ):
                # 执行断开操作
                st.session_state.bili_connected = False
                # 关闭直播间连接
                st.session_state.bili_client.stop_client()
                st.rerun()
        else:
            # 连接按钮
            if st.button(
                    "🟢 立即连接",
                    type="primary",
                    disabled=not bili_room_auth_code or not bili_access_key_id or not bili_access_key_secret or not bili_app_id,
                    help="连接到指定B站直播间" if (
                            bili_room_auth_code and bili_access_key_id and bili_access_key_secret and bili_app_id) else "请先输入直播间连接参数",
                    key="connect_btn"
            ):
                # 执行连接操作
                st.session_state.bili_connected = True
                # 初始化直播间连接
                if st.session_state.bili_client is None:
                    st.session_state.bili_client = BilibiliClient(
                        access_key_id=bili_access_key_id,
                        access_key_secret=bili_access_key_secret,
                        app_id=int(bili_app_id),
                        room_owner_id=bili_room_auth_code,
                        # 绑定大模型管理器
                        llm_manager=st.session_state.llm_manager
                    )
                else:
                    st.session_state.bili_client.ACCESS_KEY_ID = bili_access_key_id
                    st.session_state.bili_client.ACCESS_KEY_SECRET = bili_access_key_secret
                    st.session_state.bili_client.APP_ID = int(bili_app_id)
                    st.session_state.bili_client.ROOM_OWNER_AUTH_CODE = bili_room_auth_code
                # 启动直播间连接
                st.session_state.bili_client.start_client()
                st.rerun()

# 主界面
st.title("🎮 Momotalk-天童爱丽丝")
st.caption("✨ 由Streamlit提供技术支持 | 🚀 机器人助手控制台 v1.0")
st.divider()

# 状态显示区
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("🔌 连接状态")
    if st.session_state.bili_connected:
        st.success("✅ 已连接到直播间")
    else:
        st.error("❌ 未连接直播平台")

with col2:
    st.subheader("💬 对话状态")
    st.info(f"🗣️ 语音识别：{'已启用' if voice_enabled else '已禁用'}")

with col3:
    st.subheader("🧠 模型状态")
    if st.session_state.llm_manager.llm is not None:
        st.success("✅ 模型已实例化")
    else:
        st.warning("⚠️ 未实例化模型")

# ========== 聊天交互区域 ==========
st.divider()

# 聊天消息容器
chat_container = st.container()

if voice_enabled or st.session_state.bili_connected:
    st_autorefresh(interval=500, key="voice_refresh")

# 语音输入提示
text = st.session_state.voice_recognizer.get_latest_text()
if text:
    # 如果该文本还未处理，则处理并更新消息，然后刷新页面
    if not st.session_state.get("text_processed", False):
        ai_response = st.session_state.llm_manager.call_llm(prompt=f"（老师说）{text}")

sensei_avatar = get_image_as_data_uri("avatar/sensei.jpg")
alice_avatar = get_image_as_data_uri("avatar/happy.png")
# 历史消息渲染
with chat_container:
    # 显示所有消息记录
    if st.session_state.llm_manager.llm is not None:
        for i, msg in enumerate(st.session_state.llm_manager.llm.history_display):
            is_user = msg["role"] == "user"
            message(
                msg["content"],
                is_user=is_user,
                key=f"msg_{i}",
                logo=sensei_avatar if is_user else alice_avatar
            )

    if voice_enabled:
        message(
            "🎤 正在聆听...",
            is_user=True,
            key="voice_listening",
            logo=sensei_avatar,
            allow_html=True
        )

# 消息输入处理
if prompt := st.chat_input("输入消息...", disabled=True if st.session_state.llm_manager.llm is None else False):
    with chat_container:
        # 渲染新消息
        message(f"（老师说）{prompt}", is_user=True, logo=sensei_avatar,
                key=f"user_{len(st.session_state.llm_manager.llm.history_display)}")

    # AI回复
    ai_response = st.session_state.llm_manager.call_llm(prompt=f"（老师说）{prompt}")

    # 动态更新聊天区域
    with chat_container:
        # 渲染新消息
        message(remove_emotion(ai_response), is_user=False, logo=alice_avatar,
                key=f"bot_{len(st.session_state.llm_manager.llm.history_display)}")

# 自定义CSS样式
st.markdown("""
<style>
    /* 调整消息间距 */
    .stChatMessage {
        margin: 0.75rem 0;
    }

    /* 优化状态标签 */
    .stStatusLabel {
        min-height: 80px;
        padding: 1rem;
        border-radius: 8px;
    }

    /* 输入框美化 */
    [data-testid="stChatInput"] {
        border-top: 1px solid #eee;
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)
