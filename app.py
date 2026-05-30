import streamlit as st
from openai import OpenAI
import datetime

# --- БЕЗОПАСНОЕ ПОДКЛЮЧЕНИЕ КЛЮЧА ИЗ НАСТРОЕК СТРИМЛИТА ---
try:
    # Программа автоматически берет новый ключ из панели Secrets на share.streamlit.io
    groq_key = st.secrets["GROQ_API_KEY"]
except Exception:
    st.error("❌ Ошибка: Ключ GROQ_API_KEY не найден в настройках Streamlit Secrets!")
    st.stop()

# Инициализация клиента Groq через библиотеку OpenAI
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=groq_key
)

st.set_page_config(page_title="mcs AI PRO", page_icon="🤖", layout="wide")

# Кастомный CSS для красивого стиля сообщений
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; }
    div[data-testid="stForm"] { border: none !important; padding: 0 !important; }
    
    /* Уменьшение отступов вокруг кнопок в столбцах */
    .chat-input-column {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    
    /* Стилизация кнопок для компактного вида */
    div[data-testid="column"] button {
        height: auto;
        padding-top: 6px;
        padding-bottom: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ В ПАМЯТИ САЙТА ---
if "users_db" not in st.session_state:
    # Твой главный админский аккаунт для управления
    st.session_state.users_db = {
        "admin": "2026"
    }

if "audit_logs" not in st.session_state:
    # Сюда будут тайно записываться все запросы твоих друзей
    st.session_state.audit_logs = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "temp_image" not in st.session_state:
    st.session_state.temp_image = None

if "current_user" not in st.session_state:
    st.session_state.current_user = None

# Флаг для отображения меню вложений
if "show_attachments" not in st.session_state:
    st.session_state.show_attachments = False

# --- ФУНКЦИЯ ОКНА ВХОДА (АВТОРИЗАЦИЯ) ---
def check_password():
    if st.session_state.current_user is not None:
        return True

    st.title("🤖 Вход в систему mcs AI")
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    
    if st.button("Войти"):
        if username in st.session_state.users_db and st.session_state.users_db[username] == password:
            st.session_state.current_user = username
            st.rerun()
        else:
            st.error("❌ Неверный логин или пароль!")
    return False

# --- ЕСЛИ СИСТЕМА ПРОПУСТИЛА ПОЛЬЗОВАТЕЛЯ ---
if check_password():
    current_user = st.session_state.current_user

    # Боковая панель: инфо об аккаунте и кнопка выхода
    with st.sidebar:
        st.write(f"Вы вошли как: **{current_user}**")
        if st.button("🚪 Выйти из аккаунта"):
            st.session_state.current_user = None
            st.rerun()
        st.write("---")

    # ==========================================
    # 😎 РЕЖИМ АДМИНИСТРАТОРА (ВИДИТ ТОЛЬКО ADMIN)
    # ==========================================
    if current_user == "admin":
        st.title("🛡️ Главное управление mcs AI")
        
        tab1, tab2, tab3 = st.tabs(["👥 Управление пользователями", "📜 История запросов (Логи)", "🤖 Чат ассистента"])
        
        with tab1:
            st.subheader("➕ Регистрация / Смена пароля")
            new_login = st.text_input("Логин пользователя (например, user1)", key="new_login")
            new_pass = st.text_input("Пароль для этого логина", type="password", key="new_pass")
            
            if st.button("Сохранить / Изменить пользователя"):
                if new_login and new_pass:
                    # Перезаписывает пароль, если логин совпадает, сохраняя историю
                    st.session_state.users_db[new_login] = new_pass
                    st.success(f"🎉 Готово! У пользователя @{new_login} теперь пароль: {new_pass}")
                    st.rerun()
                else:
                    st.error("Заполните оба поля!")
            
            st.write("---")
            st.subheader("📋 Список всех аккаунтов в системе")
            for u, p in st.session_state.users_db.items():
                st.text(f"👤 Логин: {u}  |  🔑 Пароль: {u if u == 'admin' else p}")
                
        with tab2:
            st.subheader("🕵️ Контроль безопасности (Кто что писал)")
            if not st.session_state.audit_logs:
                st.info("Запросов пока не было. Здесь будут появляться все вопросы твоих друзей!")
            else:
                for log in reversed(st.session_state.audit_logs):
                    st.warning(f"**[{log['time']}] Пользователь @{log['user']} отправил запрос:**")
                    st.code(log['text'])
                    st.write("---")
                    
        with tab3:
            st.write("Вы зашли как главный админ. Чат с ИИ открыт ниже:")

    # Название чата для обычных пользователей
    if current_user != "admin":
        st.title(f"🤖 mcs AI — Привет, {current_user}!")
    else:
        st.write("---")

    # Вывод истории текущего чата на экран
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "image" in message and message["image"] is not None:
                st.image(message["image"], width=300)

    # --- ЗОНА ЧАТА: ВЛОЖЕНИЯ И ОТПРАВКА ---
    # Мы используем st.container() для создания "панели ввода" внизу
    with st.container():
        # Сначала обрабатываем вложения, если меню открыто
        if st.session_state.show_attachments:
            st.write("### 📎 Выберите вложение:")
            source_type = st.radio(
                "Тип источника:",
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
                st.image(uploaded_pic, caption="Фото готово к отправке!", width=150)
                if st.button("❌ Сбросить фото"):
                    st.session_state.temp_image = None
                    st.rerun()
            
            # Кнопка для закрытия меню вложений
            if st.button("Закрыть меню вложений"):
                st.session_state.show_attachments = False
                st.rerun()
            st.write("---")

        # Если фото готово, отображаем его компактно над строкой ввода
        if st.session_state.temp_image and not st.session_state.show_attachments:
             st.image(st.session_state.temp_image, caption="Готово к отправке", width=100)
             if st.button("❌ Сбросить", key="clear_ready_pic"):
                 st.session_state.temp_image = None
                 st.rerun()
             st.write("---")


        # --- СТРОКА ВВОДА С '+' СЛЕВА И '>' СПРАВА ---
        # Мы НЕ используем st.form(), так как st.camera_input и st.file_uploader не работают внутри форм.
        # Вместо этого мы используем st.columns и st.button(key=...) для управления отправкой.

        # Столбцы для кнопок
        col_attach, col_input, col_submit = st.columns([0.08, 0.84, 0.08])

        with col_attach:
            # Кнопка '+' слева. Переключает отображение меню вложений.
            if st.button("➕", key="btn_attach_add"):
                st.session_state.show_attachments = not st.session_state.show_attachments
                st.rerun()

        with col_input:
            # Поле ввода. `key="user_msg_input"` позволяет нам получить значение позже.
            placeholder_text = "Напишите вопрос к фото или просто текст..." if st.session_state.temp_image else "Спроси mcs AI о чём угодно..."
            user_input = st.text_input(
                label="Отправить сообщение...",
                label_visibility="collapsed",
                placeholder=placeholder_text,
                key="user_msg_input"
            )

        with col_submit:
            # Кнопка отправки '>' справа.
            submit_button = st.button("🚀", key="btn_chat_submit")

        # Обработка отправки (логика та же)
        if submit_button and (user_input or st.session_state.temp_image):
            full_prompt = user_input
            if st.session_state.temp_image and not user_input:
                full_prompt = "[Отправлено фото задания. Пожалуйста, разбери и реши его]"
            elif st.session_state.temp_image and user_input:
                full_prompt = f"[Фото задания] Вопрос пользователя: {user_input}"

            # 📜 Тайно записываем время, логин и текст запроса в логи админа
            now = datetime.datetime.now().strftime("%H:%M:%S")
            st.session_state.audit_logs.append({
                "time": now,
                "user": current_user,
                "text": full_prompt
            })

            # Добавляем сообщение пользователя на экран в историю
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
                                {"role": "system", "content": "Ты продвинутый школьный ИИ ассистент mcs. Помогаешь ученику 7 класса. Ты эксперт по физике, химии, геометрии, а также отлично анализируешь произведения казахской литературы и истории."},
                                {"role": "user", "content": full_prompt}
                            ],
                            model="llama3-8b-8192",
                        )
                        response = chat_completion.choices[0].message.content
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Ошибка Groq: {e}")

            # Сбрасываем временные состояния
            st.session_state.temp_image = None
            st.session_state.show_attachments = False
            # Чтобы очистить поле ввода, нам нужно его "пересоздать" или использовать более сложную логику сессии.
            # Но в Streamlit без использования st.form с clear_on_submit, самое простое - это st.rerun() после очистки ключа.
            # Это сбросит `st.session_state.user_msg_input`.
            st.session_state.user_msg_input = ""
            st.rerun()
