from fastapi import FastAPI
from backend.firebase import db  # инициализация Firebase
from backend import auth  # импорт роутов
from backend import chat

app = FastAPI()

# Подключение маршрутов авторизации
app.include_router(auth.router)
app.include_router(chat.router)

# (тестовый маршрут)
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Messenger backend работает"}

# Запуск без uvicorn вручную
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)