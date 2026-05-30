import streamlit as st
from openai import OpenAI
import datetime
import streamlit.components.v1 as components  # Компонент для работы с HTML/JS (нужен для звонков)

# --- БЕЗОПАСНОЕ ПОДКЛЮЧЕНИЕ КЛЮЧЕЙ ИЗ НАСТРОЕК СТРИМЛИТА ---
try:
    groq_key = st.secrets["GROQ_API_KEY"]
    agora_id = st.secrets["AGORA_APP_ID"]  # Безопасно забираем ID Agora, скрытый от чужих глаз
except Exception:
    st.error("❌ Ошибка: Ключи GROQ_API_KEY или AGORA_APP_ID не найдены в настройках Streamlit Secrets!")
    st.stop()

# Инициализация клиента Groq
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=groq_key
)

st.set_page_config(page_title="mcs AI PRO", page_icon="🤖", layout="wide")

# Кастомный CSS для выравнивания интерфейса
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; }
    div[data-testid="column"] button {
        width: 100% !important;
        height: 42px !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        line-height: 42px !important;
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ В ПАМЯТИ ---
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "admin": "2026"
    }

if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "temp_image" not in st.session_state:
    st.session_state.temp_image = None

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "show_attachments" not in st.session_state:
    st.session_state.show_attachments = False

# --- ФУНКЦИЯ АВТОРИЗАЦИИ ---
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

# --- ЕСЛИ ВХОД УСПЕШЕН ---
if check_password():
    current_user = st.session_state.current_user

    with st.sidebar:
        st.write(f"Вы вошли как: **{current_user}**")
        if st.button("🚪 Выйти из аккаунта"):
            st.session_state.current_user = None
            st.rerun()
        st.write("---")
        
        # ==========================================
        # 📞 ИНТЕГРАЦИЯ ЗВОНКОВ AGORA RTC (БЕЗОПАСНАЯ)
        # ==========================================
        st.subheader("📞 Голосовой звонок")
        
        AGORA_APP_ID = agora_id 
        AGORA_CHANNEL = "mcs_voice_room"

        agora_html = f"""
        <script src="https://download.agora.io/sdk/release/AgoraRTC_N-4.18.0.js"></script>
        <div style="text-align: center; font-family: sans-serif;">
            <button id="join" style="background-color: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; width: 100%; margin-bottom: 8px;">🎤 Начать звонок</button>
            <button id="leave" style="background-color: #dc3545; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; width: 100%; display: none;">📴 Отключиться</button>
            <p id="status" style="color: gray; font-size: 12px; margin-top: 5px;">Звонок не активен</p>
        </div>

        <script>
        let client = AgoraRTC.createClient({{ mode: "rtc", codec: "vp8" }});
        let localTracks = {{ audioTrack: null }};

        document.getElementById('join').onclick = async function() {{
            try {{
                // Подключаемся к комнате без токена
                await client.join("{AGORA_APP_ID}", "{AGORA_CHANNEL}", null, null);
                
                // Создаем аудиодорожку с микрофона
                localTracks.audioTrack = await AgoraRTC.createMicrophoneAudioTrack();
                
                // Публикуем её в аудиоканал
                await client.publish([localTracks.audioTrack]);
                
                document.getElementById('join').style.display = 'none';
                document.getElementById('leave').style.display = 'block';
                document.getElementById('status').innerText = "🟢 В эфире (Комната: {AGORA_CHANNEL})";
                document.getElementById('status').style.color = "green";
            }} catch (error) {{
                console.error(error);
                document.getElementById('status').innerText = "❌ Ошибка подключения: " + error.message;
                document.getElementById('status').style.color = "red";
            }}
        }};

        client.on("user-published", async (user, mediaType) => {{
            await client.subscribe(user, mediaType);
            if (mediaType === "audio") {{
                user.audioTrack.play();
            }}
        }});

        document.getElementById('leave').onclick = async function() {{
            if(localTracks.audioTrack) {{
                localTracks.audioTrack.stop();
                localTracks.audioTrack.close();
            }}
            await client.leave();
            document.getElementById('join').style.display = 'block';
            document.getElementById('leave').style.display = 'none';
            document.getElementById('status').innerText = "Звонок не активен";
            document.getElementById('status').style.color = "gray";
        }};
        </script>
        """
        # Отображаем кнопку звонка в боковом меню
        components.html(agora_html, height=150)
        st.write("---")

    # ==========================================
    # 😎 РЕЖИМ АДМИНИСТРАТОРА (ДОСТУПЕН ТОЛЬКО ADMIN)
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
                    st.session_state.users_db[new_login] = new_pass
                    st.success(f"🎉 Готово! У пользователя @{new_login} теперь пароль: {new_pass}")
                    st.rerun()
                else:
                    st.error("Заполните оба поля!")
            
            st.write("---")
            
            st.subheader("🗑️ Удаление пользователя")
            delete_login = st.text_input("Введите логин, который нужно удалить", key="delete_login")
            
            if st.button("❌ Удалить пользователя навсегда"):
                if delete_login:
                    if delete_login == "admin":
                        st.error("Вы не можете удалить главного админа!")
                    elif delete_login in st.session_state.users_db:
                        st.session_state.users_db.pop(delete_login)
                        st.success(f"🗑️ Пользователь @{delete_login} полностью удален из системы!")
                        st.rerun()
                    else:
                        st.error(f"Пользователь '{delete_login}' не найден!")
                else:
                    st.error("Введите логин для удаления!")

            st.write("---")
            st.subheader("📋 Список всех аккаунтов в системе")
            for u, p in st.session_state.users_db.items():
                st.text(f"👤 Логин: {u}  |  🔑 Пароль: {u if u == 'admin' else p}")
                
        with tab2:
            st.subheader("🕵️ Контроль безопасности (Кто что писал)")
            if not st.session_state.audit_logs:
                st.info("Запросов пока не было.")
            else:
                for log in reversed(st.session_state.audit_logs):
                    st.warning(f"**[{log['time']}] Пользователь @{log['user']} отправил запрос:**")
                    st.code(log['text'])
                    st.write("---")
                    
        with tab3:
            st.write("Вы зашли как главный админ. Чат открыт ниже.")

    if current_user != "admin":
        st.title(f"🤖 mcs AI — Привет, {current_user}!")
    else:
        st.write("---")

    # Вывод истории сообщений текущей сессии
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "image" in message and message["image"] is not None:
                st.image(message["image"], width=300)

    # --- ЗОНА ВЛОЖЕНИЙ ПО КНОПКЕ "➕" ---
    if st.session_state.show_attachments:
        st.info("📎 Меню вложений:")
        source_type = st.radio(
            "Что вы хотите прикрепить?",
            ["Ничего", "📸 Камера (Основная)", "📸 Камера (Селфи)", "🖼️ Галерея / Файлы"],
            key="attachment_source"
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
            uploaded_pic = st.file_uploader("Выберите фото или файлы", type=["jpg", "jpeg", "png"])

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
        st.write("---")

    if st.session_state.temp_image and not st.session_state.show_attachments:
         st.image(st.session_state.temp_image, caption="Готово к отправке", width=100)
         if st.button("❌ Удалить фото", key="clear_ready_pic"):
             st.session_state.temp_image = None
             st.rerun()

    # --- СТРОКА ВВОДА С ПЛЮСИКОМ СЛЕВА И РАКЕТОЙ СПРАВА ---
    col_attach, col_input, col_submit = st.columns([0.07, 0.86, 0.07])

    with col_attach:
        if st.button("➕", key="plus_btn"):
            st.session_state.show_attachments = not st.session_state.show_attachments
            st.rerun()

    with col_input:
        placeholder_text = "Напишите вопрос к фото..." if st.session_state.temp_image else "Спроси mcs AI о чём угодно..."
        user_input = st.text_input(
            label="Ввод",
            label_visibility="collapsed",
            placeholder=placeholder_text,
            key="user_msg_input"
        )

    with col_submit:
        submit_button = st.button("🚀", key="send_btn")

    # --- ОБРАБОТКА ЗАПРОСА ---
    if submit_button and (user_input or st.session_state.temp_image):
        full_prompt = user_input
        if st.session_state.temp_image and not user_input:
            full_prompt = "[Отправлено фото задания. Пожалуйста, разбери и реши его]"
        elif st.session_state.temp_image and user_input:
            full_prompt = f"[Фото задания] Вопрос пользователя: {user_input}"

        now = datetime.datetime.now().strftime("%H:%M:%S")
        st.session_state.audit_logs.append({
            "time": now,
            "user": current_user,
            "text": full_prompt
        })

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
                        model="llama-3.1-8b-instant",
                    )
                    response = chat_completion.choices[0].message.content
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Ошибка Groq: {e}")

        st.session_state.temp_image = None
        st.session_state.show_attachments = False
        st.session_state.user_msg_input = ""
        st.rerun()
