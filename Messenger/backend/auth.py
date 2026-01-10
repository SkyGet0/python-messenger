from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from firebase_admin import db
import bcrypt
import uuid
import time

router = APIRouter()

class UserCredentials(BaseModel):
    email: str
    password: str

# Регистрация
@router.post("/register")
def register_user(credentials: UserCredentials):
    email = credentials.email
    password = credentials.password

    users_ref = db.reference("users")
    all_users = users_ref.get() or {}

    for user_id, user_data in all_users.items():
        if user_data.get("email") == email:
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())

    users_ref.child(user_id).set({
        "email": email,
        "password": hashed_pw,
        "last_seen": int(time.time())
    })

    return {"message": "Регистрация прошла успешно", "user_id": user_id}

# Логин
@router.post("/login")
def login_user(credentials: UserCredentials):
    email = credentials.email
    password = credentials.password

    users_ref = db.reference("users")
    all_users = users_ref.get() or {}

    for user_id, user_data in all_users.items():
        if user_data.get("email") == email:
            stored_hash = user_data.get("password", "")
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                # обновляем last_seen при логине
                users_ref.child(user_id).update({
                    "last_seen": int(time.time())
                })
                return {"message": "Успешный вход", "user_id": user_id}
            else:
                raise HTTPException(status_code=401, detail="Неверный пароль")

    raise HTTPException(status_code=404, detail="Пользователь не найден")

# Получение списка пользователей (включая last_seen)
@router.get("/users")
def get_all_users():
    ref = db.reference("users")
    all_users = ref.get() or {}

    users = []
    for user_id, data in all_users.items():
        users.append({
            "user_id": user_id,
            "email": data.get("email", "unknown"),
            "last_seen": data.get("last_seen")
        })

    return users
