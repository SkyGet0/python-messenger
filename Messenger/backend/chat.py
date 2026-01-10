from fastapi import APIRouter
from firebase_admin import db
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import time

router = APIRouter()

class Message(BaseModel):
    sender: str
    receiver: str
    content: str
    timestamp: int

def get_chat_id(user1: str, user2: str) -> str:
    return "_".join(sorted([user1, user2]))

@router.post("/send_message")
def send_message(msg: Message):
    chat_id = get_chat_id(msg.sender, msg.receiver)
    ref = db.reference(f"chats/{chat_id}/messages")
    ref.push(msg.model_dump())
    notif_ref = db.reference(f"notifications/{msg.sender}/{msg.receiver}")
    notif_ref.set(True)
    return {"status": "ok"}

@router.get("/get_messages")
def get_messages(sender: str, receiver: str):
    chat_id = get_chat_id(sender, receiver)
    ref = db.reference(f"chats/{chat_id}/messages")
    messages_snapshot = ref.get()

    if not isinstance(messages_snapshot, dict):
        return []

    messages = []
    for message_id, message_data in messages_snapshot.items():
        message_data["id"] = message_id
        messages.append(message_data)

    return messages

@router.get("/get_new_messages")
def get_new_messages(receiver: str):
    ref = db.reference("chats")
    result = []
    all_chats = ref.get() or {}

    for chat_id, data in all_chats.items():
        if not chat_id.endswith(receiver) and not chat_id.startswith(receiver):
            continue

        for message in data.get("messages", {}).values():
            if message.get("receiver") == receiver and not message.get("read", False):
                result.append(message["sender"])
                break  # достаточно одного непрочитанного от каждого
    return list(set(result))  # уникальные отправители

@router.post("/mark_read")
def mark_messages_read(sender: str, receiver: str):
    chat_id = get_chat_id(sender, receiver)
    ref = db.reference(f"chats/{chat_id}/messages")
    messages = ref.get() or {}

    for key, msg in messages.items():
        if msg.get("receiver") == receiver and not msg.get("read"):
            ref.child(key).update({"read": True})

    # Удаление уведомления из вложенной структуры:
    notif_ref = db.reference(f"notifications/{sender}/{receiver}")
    notif_ref.delete()

    return {"status": "ok"}

@router.delete("/delete_message/{chat_id}/{message_id}")
def delete_message(chat_id: str, message_id: str):
    ref = db.reference(f"chats/{chat_id}/messages/{message_id}")
    if ref.get() is None:
        return JSONResponse(status_code=404, content={"detail": "Message not found"})
    ref.delete()
    return {"status": "deleted"}

@router.post("/update_activity")
def update_activity(user_id: str):
    ref = db.reference(f"users/{user_id}/last_seen")
    ref.set(int(time.time()))
    return {"status": "updated"}

@router.get("/users")
def get_users():
    ref = db.reference("users")
    users = ref.get() or {}
    return [{"user_id": k, "email": v.get("email"), "last_seen": v.get("last_seen", 0)} for k, v in users.items()]