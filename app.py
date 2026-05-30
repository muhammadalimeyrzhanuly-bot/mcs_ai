import streamlit as st
from openai import OpenAI
import datetime

# Инициализация клиента Groq
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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"  # <-- Твой реальный ключ Groq
)

st.set_page_config(page_title="mcs AI PRO", page_icon="🤖", layout="wide")

# Кастомный CSS для стиля ChatGPT
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; }
    div[data-testid="stForm"] { border: none !important; padding: 0 !important; }
    </style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ В ПАМЯТИ ---
if "users_db" not in st.session_state:
    # Изначально есть только главный админ
    st.session_state.users_db = {
        "admin": "2026"
    }

if "audit_logs" not in st.session_state:
    # База логов: кто, в какое время и какой запрос отправил
    st.session_state.audit_logs = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "temp_image" not in st.session_state:
    st.session_state.temp_image = None

if "current_user" not in st.session_state:
    st.session_state.current_user = None

# --- ФУНКЦИЯ АВТОРИЗАЦИИ ---
def check_password():
    if st.session_state.current_user is not None:
        return True

    st.title("🤖 Вход в систему mcs AI")
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    
    if st.button("Войти"):
        # Проверяем, есть ли такой юзер в нашей созданной базе и совпадает ли пароль
        if username in st.session_state.users_db and st.session_state.users_db[username] == password:
            st.session_state.current_user = username
            st.rerun()
        else:
            st.error("❌ Неверный логин или пароль!")
    return False

# --- ЕСЛИ ВХОД ВЫПОЛНЕН УСПЕШНО ---
if check_password():
    current_user = st.session_state.current_user

    # Кнопка выхода из аккаунта вверху бокового меню
    with st.sidebar:
        st.write(f"Вы вошли как: **{current_user}**")
        if st.button("🚪 Выйти из аккаунта"):
            st.session_state.current_user = None
            st.rerun()
        st.write("---")

    # ==========================================
    # 😎 РЕЖИМ АДМИНИСТРАТОРА (ДОСТУПЕН ТОЛЬКО ADMIN)
    # ==========================================
    if current_user == "admin":
        st.title("🛡️ Главное управление mcs AI")
        
        tab1, tab2, tab3 = st.tabs(["👥 Управление пользователями", "📜 История запросов (Логи)", "🤖 Чат ассистента"])
        
        with tab1:
            st.subheader("➕ Регистрация нового пользователя")
            new_login = st.text_input("Придумайте логин для друга (например, user1)", key="new_login")
            new_pass = st.text_input("Придумайте пароль", type="password", key="new_pass")
            
            if st.button("Зарегистрировать пользователя"):
                if new_login and new_pass:
                    if new_login in st.session_state.users_db:
                        st.error(f"Пользователь '{new_login}' уже существует!")
                    else:
                        st.session_state.users_db[new_login] = new_pass
                        st.success(f"🎉 Пользователь '{new_login}' успешно создан! Его пароль: {new_pass}")
                        st.rerun()
                else:
                    st.error("Заполните оба поля!")
            
            st.write("---")
            st.subheader("📋 Список всех аккаунтов в системе")
            for u, p in st.session_state.users_db.items():
                st.text(f"👤 Логин: {u}  |  🔑 Пароль: {u if u == 'admin' else p}") # Пароль админа скрыт для безопасности
                
        with tab2:
            st.subheader("🕵️ Контроль безопасности (Кто что писал)")
            if not st.session_state.audit_logs:
                st.info("Запросов пока не было. Здесь будет отображаться всё, что пишут твои друзья!")
            else:
                for log in reversed(st.session_state.audit_logs):
                    st.warning(f"**[{log['time']}] Пользователь @{log['user']} отправил запрос:**")
                    st.code(log['text'])
                    st.write("---")
                    
        with tab3:
            st.write("Здесь ты можешь общаться с ИИ как админ.")
            # Чат для админа будет отображаться ниже, вкладка просто разделяет экраны

    # ==========================================
    # 🤖 ОБЫЧНЫЙ ИНТЕРФЕЙС ЧАТА (ДЛЯ ВСЕХ)
    # ==========================================
    if current_user != "admin":
        st.title(f"🤖 mcs AI — Привет, {current_user}!")
    else:
        st.write("---")

    # Отображение истории сообщений
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "image" in message and message["image"] is not None:
                st.image(message["image"], width=300)

    # --- ЗОНА ПЛЮСИКА (Слева в боковой панели) ---
    with st.sidebar:
        st.subheader("📎 Вложения (Плюсик)")
        source_type = st.radio(
            "Что прикрепить к сообщению?",
            ["Ничего", "📸 Камера (Основная)", "📸 Камера (Селфи)", "🖼️ Галерея / Файлы"]
        )
        
        uploaded_pic = None
        facing_mode = None
        
        if source_type == "📸 Камера (Основная)":
            uploaded_pic = st.camera_input("Сделайте снимок задания")
            facing_mode = "environment"
        elif source_type == "📸 Камера (Селфи)":
            uploaded_pic = st.camera_input("Сделайте селфи")
            facing_mode = "user"
        elif source_type == "🖼️ Галерея / Файлы":
            uploaded_pic = st.file_uploader("Выберите фото из галереи", type=["jpg", "jpeg", "png"])

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
            st.image(uploaded_pic, caption="Фото готово!", width=150)
            if st.button("❌ Сбросить фото"):
                st.session_state.temp_image = None
                st.rerun()

    # --- СТРОКА ВВОДА СТИЛЬ CHATGPT ---
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
                submit_button = st.form_submit_button(label="🚀")

        if submit_button and (user_input or st.session_state.temp_image):
            full_prompt = user_input
            if st.session_state.temp_image and not user_input:
                full_prompt = "[Отправлено фото задания. Пожалуйста, разбери и реши его]"
            elif st.session_state.temp_image and user_input:
                full_prompt = f"[Фото задания] Вопрос пользователя: {user_input}"

            # 📜 ЗАПИСЬ В ЛОГИ ДЛЯ АДМИНА
            now = datetime.datetime.now().strftime("%H:%M:%S")
            st.session_state.audit_logs.append({
                "time": now,
                "user": current_user,
                "text": full_prompt
            })

            # Добавляем в историю на экране
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
                                {"role": "system", "content": "Ты продвинутый школьный ИИ ассистент mcs. Помогаешь ученику 7 класса."},
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
