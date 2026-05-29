import streamlit as st
from openai import OpenAI
from datetime import datetime

# --- 1. НАСТРОЙКА ИНТЕРФЕЙСА MCS ---
st.set_page_config(page_title="mcs AI", page_icon="🤖")
st.title("🤖 mcs")
st.write("Твой личный ИИ-помощник по школьной программе")

# --- 2. БИЗНЕС-БЛОК: СПИСОК КЛИЕНТОВ (ПОДПИСЧИКОВ) ---
# Когда кто-то покупает подписку, просто дописывай его логин сюда через запятую!
# Пиши строго маленькими английскими буквами.
ALLOWED_USERS = ["user", "asan", "ilyas", "admin", "test"]

# --- 3. СИСТЕМА АВТО-ПАРОЛЕЙ НА КАЖДЫЙ ДЕНЬ ---
st.sidebar.title("🔑 Вход в систему mcs")
user_login = st.sidebar.text_input("Введи свой логин:", value="").lower().strip()
user_password = st.sidebar.text_input("Введи пароль дня:", type="password")

# Компьютер сам берет текущую дату (день и месяц)
today = datetime.now()
current_date = today.strftime("%d%m")  # Сегодня (29 мая) это будет "2905"

# Проверка: есть ли вообще такой логин в нашей базе?
if user_login not in ALLOWED_USERS:
    st.sidebar.warning("❌ Такого логина нет в системе mcs!")
    st.stop()

# Робот вычисляет уникальный пароль для этого логина на СЕГОДНЯ
# Например для 'asan' сегодня пароль будет: 2905asan
CORRECT_PASSWORD = f"{current_date}{user_login}"

# Проверка пароля
if user_password != CORRECT_PASSWORD:
    st.sidebar.error("🔒 Неверный пароль дня для этого логина!")
    st.sidebar.info("Подсказка: пароль обновляется автоматически каждые 24 часа.")
    st.stop()

# Если логин и пароль совпали — открываем доступ
st.sidebar.success(f"🔓 Доступ разрешен! Привет, {user_login}!")


# --- 4. ПОДКЛЮЧЕНИЕ НЕЙРОСЕТИ ---
# ВНИМАНИЕ: Вставь ниже свой настоящий ключ вместо gsk_ТВОЙ_КЛЮЧ_ИЗ_GROQ!
API_KEY = "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" 
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=API_KEY)


# --- 5. ФУНКЦИЯ КАМЕРЫ ДЛЯ СФОТКАННОЙ ДОМАШКИ ---
photo = st.camera_input("📸 Сделать фото задания для mcs")
if photo:
    st.image(photo, caption="Снимок успешно загружен в систему!")


# --- 6. ПАМЯТЬ ЧАТА И КЛИЕНТ-СЕРВЕРНАЯ ЧАСТЬ ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Отображаем старые сообщения на экране
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Поле для ввода вопроса пользователем
if user_input := st.chat_input("Напиши что-нибудь своему ИИ mcs..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        try:
            # СЕКРЕТНАЯ ИНСТРУКЦИЯ (Пункт 2), которая делает ИИ умным школьником
            system_instruction = (
                "Ты — специализированный ИИ-помощник по имени mcs, созданный для помощи ученикам в Казахстане. "
                "Ты идеально знаешь учебную программу, правила и темы (включая СОР и ТЖБ) для 7 класса. "
                "Твоя задача — помогать решать задачи по физике, химии, геометрии, делать разборы по казахской и русской литературе. "
                "ВАЖНО: Пиши ответы простым, понятным языком, без заумных фраз и без явных признаков того, что это писал робот. "
                "Твой стиль должен быть полностью похож на ответ обычного живого умного ученика, чтобы учителя не догадались о списывании. "
                "Отвечай кратко, четко, структурировано и по делу."
            )

            # Собираем историю диалога и добавляем скрытую инструкцию наверх
            messages_to_send = [{"role": "system", "content": system_instruction}]
            for m in st.session_state.messages:
                messages_to_send.append({"role": m["role"], "content": m["content"]})

            # Запрос к серверу Groq с новой моделью Llama 3.1
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages_to_send
            )
            
            ai_response = completion.choices[0].message.content
            response_placeholder.markdown(ai_response)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
        except Exception as e:
            st.error(f"Ошибка сервера Groq. Проверь свой API_KEY в коде! Текст ошибки: {e}")