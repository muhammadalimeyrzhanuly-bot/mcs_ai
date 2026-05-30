import streamlit as st
from openai import OpenAI

# Инициализация клиента Groq / OpenAI
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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"  # <-- Вставь сюда свой реальный ключ Groq
)

st.set_page_config(page_title="mcs AI", page_icon="🤖", layout="wide")

# Кастомный CSS для стиля ChatGPT
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; }
    .chat-input-container { display: flex; align-items: center; gap: 10px; }
    div[data-testid="stForm"] { border: none !important; padding: 0 !important; }
    </style>
""", unsafe_allow_html=True)

# Функция проверки уникальной закономерности
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🤖 Вход в mcs AI")
        username = st.text_input("Логин (admin, user1, user2...)")
        password = st.text_input("Пароль", type="password")
        
        if st.button("Войти"):
            # Проверка админа
            if username == "admin" and password == "2026":
                st.session_state.authenticated = True
                st.rerun()
            # Проверка пользователей по закономерности: (номер * 7) + 2026
            elif username.startswith("user"):
                try:
                    user_num = int(username.replace("user", "")) # Точка исправлена!
                    expected_password = str((user_num * 7) + 2026)
                    if password == expected_password:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Неверный пароль!")
                except ValueError:
                    st.error("Неверный формат логина!")
            else:
                st.error("Пользователь не найден!")
        return False
    return True

if check_password():
    # Инициализация истории чата
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "temp_image" not in st.session_state:
        st.session_state.temp_image = None

    st.title("🤖 mcs AI")

    # Отображение истории чата
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "image" in message and message["image"] is not None:
                st.image(message["image"], width=300)

    # --- ЗОНА ПЛЮСИКА (Боковое меню слева) ---
    with st.sidebar:
        st.subheader("📎 Вложения (Плюсик)")
        source_type = st.radio(
            "Что прикрепить к сообщению?",
            ["Ничего", "📸 Камера (Основная)", "📸 Камера (Селфи)", "🖼️ Галерея / Файлы"]
        )
        
        uploaded_pic = None
        if source_type == "📸 Камера (Основная)":
            uploaded_pic = st.camera_input("Сделайте снимок задания")
            facing_mode = "environment"
        elif source_type == "📸 Камера (Селфи)":
            uploaded_pic = st.camera_input("Сделайте селфи")
            facing_mode = "user"
        elif source_type == "🖼️ Галерея / Файлы":
            uploaded_pic = st.file_uploader("Выберите фото из галереи", type=["jpg", "jpeg", "png"])
            facing_mode = None

        if facing_mode and source_type != "Ничего":
            st.components.v1.html(
                f"""<script>
                const video = parent.document.querySelector('video');
                if (video && video.srcObject) {{
                    const constraints = {{ video: {{ facingMode: "{facing_mode}" }} }};
                    navigator.mediaDevices.getUserMedia(constraints).then(stream => {{ video.srcObject = stream; }});
                }}
                </script>""", height=0
            )

        if uploaded_pic:
            st.session_state.temp_image = uploaded_pic
            st.image(uploaded_pic, caption="Фото готово к отправке!", width=150)
            if st.button("❌ Сбросить фото"):
                st.session_state.temp_image = None
                st.rerun()

    # --- СТРОКА ВВОДА С КНОПКОЙ ОТПРАВИТЬ СПРАВА ---
    with st.container():
        with st.form(key="chat_form", clear_on_submit=True):
            cols = st.columns([0.88, 0.12])
            with cols[0]:
                user_input = st.text_input(
                    label="Отправить сообщение...",
                    label_visibility="collapsed",
                    placeholder="Напишите вопрос к фото или просто текст..." if st.session_state.temp_image else "Спроси mcs AI о чём угодно..."
                )
            with cols[1]:
                submit_button = st.form_submit_button(label="🚀 Отправить")

        if submit_button and (user_input or st.session_state.temp_image):
            full_prompt = user_input
            if st.session_state.temp_image and not user_input:
                full_prompt = "[Отправлено фото задания. Пожалуйста, разбери и реши его]"
            elif st.session_state.temp_image and user_input:
                full_prompt = f"[Фото задания] Вопрос пользователя: {user_input}"

            st.session_state.messages.append({
                "role": "user", 
                "content": full_prompt, 
                "image": st.session_state.temp_image
            })

            with st.chat_message("assistant"):
                with st.spinner("mcs думает..."):
                    try:
                        chat_completion = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": "Ты продвинутый школьный ИИ ассистент mcs. Помогаешь ученику 7 класса, объясняешь темы по физике, химии, истории и литературе Казахстана."},
                                {"role": "user", "content": full_prompt}
                            ],
                            model="llama3-8b-8192",
                        )
                        response = chat_completion.choices[0].message.content
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Ошибка Groq: {e}")

            st.session_state.temp_image = None
            st.rerun()
