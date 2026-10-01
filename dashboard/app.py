import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt

st.set_page_config(page_title="HRM DNA ML Service", layout="wide")

st.title("🧬 DNA Melting Curve Genotyping Service")
st.markdown("Панель аналитики, управления балансом и экспресс-анализа кривых плавления ДНК.")

# Инициализация сессии авторизации
if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

API_URL = "http://web:8000/api/v1"

# Сайдбар авторизации
with st.sidebar:
    st.header("🔑 Авторизация")
    if not st.session_state.token:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        if col1.button("Войти"):
            res = requests.post(f"{API_URL}/users/login", data={"username": email, "password": password})
            if res.status_code == 200:
                st.session_state.token = res.json()["access_token"]
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("Ошибка авторизации")
        if col2.button("Регистрация"):
            res = requests.post(f"{API_URL}/users/register", json={"email": email, "password": password})
            if res.status_code == 200:
                st.success("Успешно! Теперь войдите")
            else:
                st.error("Ошибка регистрации")
    else:
        st.write(f"Вы вошли как: **{st.session_state.user_email}**")
        if st.button("Выйти"):
            st.session_state.token = None
            st.session_state.user_email = ""
            st.rerun()

if st.session_state.token:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # Запрос данных текущего юзера
    user_info = requests.get(f"{API_URL}/users/me", headers=headers).json()

    # 1. Биллинг & Промокоды
    st.header("💳 Мой Баланс и Финансы")
    c1, c2, c3 = st.columns(3)
    c1.metric("Баланс (Реальные кредиты)", f"{user_info.get('cash_credits')} 🪙")
    c2.metric("Бонусные кредиты (Промо)", f"{user_info.get('bonus_credits')} 🎁")

    # Блок пополнения
    top_up_amount = c3.number_input("Пополнение счета", min_value=10.0, step=10.0)
    if c3.button("Пополнить (Mock Pay)"):
        requests.post(f"{API_URL}/billing/top-up", json={"amount": top_up_amount}, headers=headers)
        st.rerun()

    st.subheader("🎟 Активация промокода")
    promo_code = st.text_input("Введите промокод (попробуйте WELCOME100)", "")
    if st.button("Активировать"):
        res = requests.post(f"{API_URL}/billing/promo/activate", json={"code": promo_code}, headers=headers)
        if res.status_code == 200:
            st.success("Успешно зачислено 100 промо-кредитов!")
            st.rerun()
        else:
            st.error(res.json().get("detail", "Ошибка"))

    # 2. Анализ HRM кривых
    st.header("🧬 Анализ Кривых Плавления (HRM)")

    # Предлагаем скачать или сгенерировать демо-файл
    if st.checkbox("Использовать демо-сигнал (эмуляция реального теста)"):
        # Генерируем красивую кривую
        temps = np.linspace(70.0, 90.0, 100)
        # Генерируем гетерозиготу (две стадии плавления)
        fluo = 0.5 / (1.0 + np.exp((temps - 78.5) / 0.4)) + 0.5 / (
                    1.0 + np.exp((temps - 80.5) / 0.4)) + 0.5 - 0.003 * temps
        df_demo = pd.DataFrame({"temperature": temps, "fluorescence": fluo})
    else:
        analysis_mode = st.radio(
            "Источник данных:",
            ["Загрузить свой CSV", "✨ Использовать эталон uMelt (rpoB / Туберкулез-Рифампицин)"]
        )

        df_demo = None

        if "uMelt" in analysis_mode:
            st.info("💡 Модельный профиль плавления гена rpoB. Расходует бесплатную демо-попытку!")
            mut_choice = st.selectbox(
                "Выберите вариант последовательности rpoB:",
                ["WT (Дикий тип)", "S531L (Мутация транзиция)", "D516V (Мутация транстверсия)"]
            )
            temps = np.linspace(58.0, 98.0, 201)
            base_f = 100.0 / (1.0 + np.exp((temps - 87.5) / 0.45))
            bg = 170.0 - 0.5 * np.exp(0.04 * (temps - 76.1))
            noise = np.random.normal(0, 0.3, len(temps))
            fluo = base_f + bg + noise
            df_demo = pd.DataFrame({"temperature": temps, "fluorescence": fluo})
        else:
            uploaded_file = st.file_uploader("Загрузите CSV с кривыми плавления", type=["csv"])
            df_demo = None

            if uploaded_file is not None:
                # Читаем CSV
                df_raw = pd.read_csv(uploaded_file)

                # Проверяем, как названы колонки или ищем их по смыслу
                cols = [str(c).lower().strip() for c in df_raw.columns]

                # Если файл транспонированный (температура в колонках, либо первый столбец - температуры)
                if "temperature" in cols and "fluorescence" in cols:
                    # Классический вертикальный формат
                    temp_col = df_raw.columns[cols.index("temperature")]
                    fluo_col = df_raw.columns[cols.index("fluorescence")]
                    df_demo = pd.DataFrame({
                        "temperature": df_raw[temp_col].astype(float),
                        "fluorescence": df_raw[fluo_col].astype(float)
                    })
                else:
                    # Если это матрица данных (как ваш файл на скриншоте):
                    # Берем первый столбец как температуру, а второй (или выбранный) как флуоресценцию
                    st.info("💡 Обнаружена матрица данных. Преобразуем автоматически...")

                    # Предположим, первая колонка - температуры
                    temperatures = pd.to_numeric(df_raw.iloc[:, 0], errors='coerce').values

                    # Выбор столбца с флуоресценцией
                    val_cols = df_raw.columns[1:]
                    chosen_col = st.selectbox("Выберите столбец (лунку) с флуоресценцией:", val_cols)

                    fluorescence = pd.to_numeric(df_raw[chosen_col], errors='coerce').values

                    df_demo = pd.DataFrame({
                        "temperature": temperatures,
                        "fluorescence": fluorescence
                    }).dropna()  # Убираем пустые строки, если есть

    if df_demo is not None:
        st.write("Исходные данные:")
        st.dataframe(df_demo.head())

        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        ax[0].plot(df_demo["temperature"], df_demo["fluorescence"], 'r.-')
        ax[0].set_title("Сырая кривая плавления F(T)")
        ax[0].set_xlabel("T, °C")
        ax[0].set_ylabel("Флуоресценция")

        # Считаем производную для визуализации пика Tm
        df = -np.gradient(df_demo["fluorescence"], df_demo["temperature"])
        ax[1].plot(df_demo["temperature"], df, 'b.-')
        ax[1].set_title("Производная -dF/dT (Пик Tm)")
        ax[1].set_xlabel("T, °C")
        ax[1].set_ylabel("-dF/dT")
        st.pyplot(fig)

        if st.button("🚀 Начать ML-генотипирование (1 кредит)"):
            payload = {
                "temperatures": df_demo["temperature"].tolist(),
                "fluorescence": df_demo["fluorescence"].tolist()
            }
            res_pred = requests.post(f"{API_URL}/ml/predict", json=payload, headers=headers)
            if res_pred.status_code == 200:
                task_id = res_pred.json()["task_id"]
                st.info(f"Задача добавлена в очередь Celery. ID: {task_id}")

                # Пулл результатов
                import time

                with st.spinner("Выполняем асинхронный расчет модели..."):
                    for _ in range(10):
                        time.sleep(1)
                        status_res = requests.get(f"{API_URL}/ml/result/{task_id}").json()
                        if status_res["status"] == "completed":
                            st.success(f"Анализ завершен! Генотип: **{status_res['genotype']}**")
                            st.metric("Уверенность модели", f"{round(status_res['confidence'] * 100, 2)} %")
                            st.metric("Рассчитанная температура плавления (Tm)", f"{status_res['tm']} °C")

                            st.write("Вероятности классов:")
                            st.json(status_res["probabilities"])
                            break
                        elif status_res["status"] == "failed":
                            st.error(f"Ошибка вычислений: {status_res['error']}")
                            break
            else:
                st.error(res_pred.json().get("detail", "Ошибка баланса"))
else:
    st.warning("Пожалуйста, зарегистрируйтесь или войдите, чтобы начать работу с сервисом.")