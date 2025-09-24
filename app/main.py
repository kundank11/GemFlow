from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.supabase_client import supabase
from app.gemini_client import send_to_gemini
from typing import Optional
import uuid
from datetime import datetime


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    user_id: Optional[str] = None

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        if not req.chat_id:
            req.chat_id = str(uuid.uuid4())
            supabase.table("chats").insert({
                "id": req.chat_id,
                "user_id": req.user_id,
                "title": (req.message or "")[:50],
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        supabase.table("messages").insert({
            "chat_id": req.chat_id,
            "role": "user",
            "content": req.message,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        reply = send_to_gemini(req.message) or "[no reply from gemini]"

        supabase.table("messages").insert({
            "chat_id": req.chat_id,
            "role": "assistant",
            "content": reply,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        return {
            "chat_id": req.chat_id,
            "reply": reply
        }
    except Exception as e:
        print("Exception in /chat:", e)
        return {"error": "internal_server_error", "details": str(e)}

@app.get("/chats")
def list_chats(user_id: str = Query(..., description="user id to list chats for")):
    response = (
        supabase.table("chats")
        .select("id, title, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    chats = response.data if response.data else []
    return {"user_id": user_id, "chats": chats}

@app.get("/chat/{chat_id}")
def get_chat(chat_id: str):
    try:
        msgs_resp = (
            supabase.table("messages")
            .select("role, content, created_at")
            .eq("chat_id", chat_id)
            .order("created_at", desc=False)
            .execute()
        )
        messages = msgs_resp.data if msgs_resp.data else []
        return {
            "chat_id": chat_id,
            "messages": messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
