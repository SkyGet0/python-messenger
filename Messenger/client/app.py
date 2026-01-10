import flet as ft
import httpx
import time
import threading
from datetime import datetime

API_URL = "http://127.0.0.1:8000"

def get_colors(theme: str):
    if theme == "light":
        return {
            "bg": "#ffffff",
            "text": "#000000",
            "container": "#f0f0f0",
            "border": "#cccccc",
            "bubble_self": "#dcf8c6",
            "bubble_other": "#eeeeee",
            "secondary": "#888888"
        }
    else:
        return {
            "bg": "#111111",
            "text": "#ffffff",
            "container": "#1e1e1e",
            "border": "#444",
            "bubble_self": "#2f3136",
            "bubble_other": "#1e1e1e",
            "secondary": "#888888"
        }

def show_user_list(page: ft.Page, user_id: str, colors: dict):
    import threading
    import time
    from datetime import datetime

    page.title = "Выбор собеседника"
    page.controls.clear()

    users_column = ft.Column(scroll=ft.ScrollMode.AUTO)
    new_messages_from = set()

    def load_users():
        try:
            response = httpx.get(f"{API_URL}/users")
            if response.status_code == 200:
                users = response.json()
                users_column.controls.clear()

                for user in users:
                    if user["user_id"] == user_id:
                        continue

                    def open_chat(e, target_id=user["user_id"]):
                        page.session.set("receiver_id", target_id)
                        show_chat_interface(page, user_id, target_id, colors)

                    has_new = user["user_id"] in new_messages_from

                    last_seen = user.get("last_seen")
                    if last_seen:
                        elapsed = int(time.time()) - last_seen
                        if elapsed < 60:
                            activity_text = "Онлайн"
                            activity_color = "green"
                        elif elapsed < 3600:
                            minutes = elapsed // 60
                            activity_text = f"Был(а) {minutes} мин назад"
                            activity_color = colors["secondary"]
                        elif elapsed < 86400:
                            hours = elapsed // 3600
                            activity_text = f"Был(а) {hours} ч назад"
                            activity_color = colors["secondary"]
                        else:
                            dt = datetime.fromtimestamp(last_seen)
                            activity_text = f"Был(а) {dt.strftime('%d.%m %H:%M')}"
                            activity_color = colors["secondary"]
                    else:
                        activity_text = "Нет данных"
                        activity_color = colors["secondary"]

                    users_column.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(user["email"], color=colors["text"]),
                                    ft.Text(" 🔔", color="green") if has_new else ft.Text(""),
                                    ft.TextButton("Открыть чат", on_click=open_chat)
                                ]),
                                ft.Text(activity_text, size=12, color=activity_color)
                            ]),
                            padding=10,
                            bgcolor=colors["container"],
                            border_radius=8,
                            margin=5
                        )
                    )

                page.update()
        except Exception as err:
            print("Ошибка загрузки пользователей:", err)

    def poll_new_messages():
        while True:
            try:
                response = httpx.get(f"{API_URL}/get_new_messages", params={"receiver": user_id})
                if response.status_code == 200:
                    senders = response.json()  # список user_id
                    new_messages_from.clear()
                    new_messages_from.update(senders)
                    load_users()
            except Exception as e:
                print("Ошибка обновления уведомлений:", e)
            time.sleep(5)

    threading.Thread(target=poll_new_messages, daemon=True).start()

    load_users()

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("Выберите собеседника", size=22, weight=ft.FontWeight.BOLD, color=colors["text"]),
                ft.Divider(),
                users_column
            ]),
            padding=20
        )
    )
    page.update()

def show_chat_interface(page: ft.Page, user_id: str, receiver_id: str, colors: dict):
    chat_id = "_".join(sorted([user_id, receiver_id]))
    page.title = "Messenger Chat"
    page.controls.clear()
    chat_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    input_field = ft.TextField(hint_text="Введите сообщение...", expand=True)
    send_btn = ft.ElevatedButton("Отправить", width=100)

    def load_messages():
        try:
            response = httpx.get(f"{API_URL}/get_messages", params={
                "sender": user_id,
                "receiver": receiver_id
            })

            if response.status_code == 200:
                messages = response.json()
                chat_column.controls.clear()

                for msg in messages:
                    is_self = msg["sender"] == user_id
                    sender_label = "(Вы)" if is_self else msg["sender"]
                    time_str = datetime.fromtimestamp(msg["timestamp"]).strftime("%H:%M")

                    message_content = ft.Column([
                        ft.Text(sender_label, size=12, color=colors["secondary"]),
                        ft.Text(msg["content"], size=14, color=colors["text"]),
                        ft.Text(time_str, size=10, color=colors["secondary"], italic=True,
                                text_align=ft.TextAlign.RIGHT),
                    ])

                    if is_self and "id" in msg:
                        delete_btn = ft.TextButton(
                            text="Удалить",
                            style=ft.ButtonStyle(padding=4, bgcolor="#aa0000", color="white"),
                            on_click=lambda e, mid=msg["id"]: delete_message(chat_id, mid)
                        )
                        message_content.controls.append(delete_btn)

                    bubble = ft.Row([
                        ft.Container(
                            content=message_content,
                            padding=10,
                            margin=5,
                            bgcolor=colors["bubble_self"] if is_self else colors["bubble_other"],
                            border_radius=10,
                            alignment=ft.alignment.center_right if is_self else ft.alignment.center_left,
                            # width=500  ← убираем
                        )
                    ], alignment=ft.MainAxisAlignment.END if is_self else ft.MainAxisAlignment.START)
                    chat_column.controls.append(bubble)

                page.update()

                try:
                    httpx.post(f"{API_URL}/mark_read", params={
                        "sender": receiver_id,
                        "receiver": user_id
                    })
                except Exception as e:
                    print("Ошибка сброса уведомлений:", e)

            else:
                print("Ошибка получения:", response.status_code, response.text)

        except Exception as e:
            print("Ошибка загрузки сообщений:", e)

    def send_message(e=None):
        if input_field.value.strip() == "":
            return
        try:
            httpx.post(f"{API_URL}/send_message", json={
                "sender": user_id,
                "receiver": receiver_id,
                "content": input_field.value,
                "timestamp": int(time.time())
            })
            input_field.value = ""
            load_messages()
        except Exception as e:
            print("Ошибка отправки сообщения:", e)
        page.update()

    def delete_message(chat_id: str, message_id: str):
        try:
            response = httpx.delete(f"{API_URL}/delete_message/{chat_id}/{message_id}")
            if response.status_code == 200:
                load_messages()
            else:
                print("Не удалось удалить:", response.text)
        except Exception as e:
            print("Ошибка удаления:", e)

    def auto_refresh():
        while True:
            load_messages()
            time.sleep(3)

    send_btn.on_click = send_message
    input_field.on_submit = send_message
    threading.Thread(target=auto_refresh, daemon=True).start()

    page.add(
        ft.Column([
            ft.Row([
                ft.ElevatedButton(
                    text="Назад к списку",
                    on_click=lambda e: show_user_list(page, user_id, colors),
                    icon=ft.Icons.ARROW_BACK,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=6),
                        padding=8,
                        bgcolor="#333"
                    )
                )
            ], alignment=ft.MainAxisAlignment.START),

            ft.Row([
                ft.Text("Чат", size=20, weight=ft.FontWeight.BOLD, color=colors["text"])
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),

            ft.Row([
                ft.Container(
                    content=chat_column,
                    bgcolor=colors["container"],
                    padding=15,
                    border_radius=10,
                    width=600,
                    height=450
                )
            ], alignment=ft.MainAxisAlignment.CENTER),

            ft.Row(
                controls=[input_field, send_btn],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
            )
        ],
            expand=True,
            spacing=20,
            alignment=ft.MainAxisAlignment.START
        )
    )
    page.update()

def main(page: ft.Page):
    import time

    theme = page.client_storage.get("theme") or "dark"
    colors = get_colors(theme)

    def toggle_theme(e):
        nonlocal theme, colors, theme_switch
        theme = "light" if theme == "dark" else "dark"
        page.client_storage.set("theme", theme)
        colors = get_colors(theme)
        page.clean()
        main(page)

    page.title = "Messenger Login"
    page.bgcolor = colors["bg"]
    page.window_width = 800
    page.window_height = 600
    page.window_resizable = False
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    mode = "login"
    email = ft.TextField(
        label="Email", width=300, bgcolor=colors["container"],
        border_radius=8, border_color=colors["border"], color=colors["text"]
    )
    password = ft.TextField(
        label="Password", password=True, can_reveal_password=True,
        width=300, bgcolor=colors["container"],
        border_radius=8, border_color=colors["border"], color=colors["text"]
    )
    message = ft.Text(value="", color="red")

    theme_switch = ft.Switch(
        label="Тёмная тема" if theme == "dark" else "Светлая тема",
        value=(theme == "dark"),
        on_change=toggle_theme
    )

    def toggle_mode(e):
        nonlocal mode
        mode = "register" if mode == "login" else "login"
        submit_btn.text = "Зарегистрироваться" if mode == "register" else "Войти"
        toggle_btn.text = "Уже есть аккаунт? Войти" if mode == "register" else "Нет аккаунта? Зарегистрироваться"
        message.value = ""
        page.update()

    def submit(e):
        submit_btn.disabled = True
        submit_btn.text = "Подождите..."
        message.value = ""
        page.update()
        try:
            response = httpx.post(
                f"{API_URL}/{mode}",
                json={"email": email.value, "password": password.value},
                timeout=5
            )
            if response.status_code == 200:
                user_id = response.json().get("user_id")
                page.session.set("user_id", user_id)

                # Первичная запись активности
                try:
                    httpx.post(f"{API_URL}/update_activity", params={"user_id": user_id})
                except Exception as err:
                    print("Ошибка обновления активности:", err)

                # Постоянное обновление активности
                import threading
                def keep_alive():
                    while True:
                        try:
                            httpx.post(f"{API_URL}/update_activity", params={"user_id": user_id})
                        except Exception as err:
                            print("keep_alive ошибка:", err)
                        time.sleep(20)

                threading.Thread(target=keep_alive, daemon=True).start()
                show_user_list(page, user_id, colors)
        except Exception as err:
            message.value = f"Ошибка соединения: {err}"

        submit_btn.disabled = False
        submit_btn.text = "Зарегистрироваться" if mode == "register" else "Войти"
        page.update()

    submit_btn = ft.ElevatedButton("Войти", on_click=submit, width=300, height=45)
    toggle_btn = ft.TextButton("Нет аккаунта? Зарегистрироваться", on_click=toggle_mode)

    page.add(
        theme_switch,
        ft.Container(
            content=ft.Column([
                ft.Text("Messenger", size=24, weight=ft.FontWeight.BOLD, color=colors["text"]),
                email,
                password,
                submit_btn,
                toggle_btn,
                message
            ], spacing=15,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30,
            bgcolor=colors["container"],
            border_radius=10,
            shadow=ft.BoxShadow(blur_radius=20, color="#00000088", spread_radius=2),
        )
    )

ft.app(target=main)