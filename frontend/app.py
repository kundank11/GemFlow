import streamlit as st
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import sys, os

import supabase_client as sb  
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))
from gemini_client import send_to_gemini


st.set_page_config(page_title="GemFlow — Chat", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages: List[Dict] = []
if "chat_id" not in st.session_state:
    st.session_state.chat_id: Optional[str] = None
if "user" not in st.session_state:
    st.session_state.user = None
if "chats" not in st.session_state:
    st.session_state.chats: List[Dict] = []

def append_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def _get_supabase_client_for_frontend():
    return sb._get_client()

def call_backend_send(message: str):
    client = _get_supabase_client_for_frontend()
    chat_id = st.session_state.chat_id
    user_id = st.session_state.user["id"] if st.session_state.user else None

    if not chat_id:
        chat_id = str(uuid.uuid4())
        client.table("chats").insert({
            "id": chat_id,
            "user_id": user_id,
            "title": (message or "")[:50],
            "created_at": datetime.utcnow().isoformat()
        }).execute()

    client.table("messages").insert({
        "chat_id": chat_id,
        "role": "user",
        "content": message,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    reply = send_to_gemini(message) or "[no reply from gemini]"

    client.table("messages").insert({
        "chat_id": chat_id,
        "role": "assistant",
        "content": reply,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return reply, chat_id

def load_chat_by_id(chat_id: str):
    try:
        client = _get_supabase_client_for_frontend()
        resp = client.table("messages") \
            .select("role, content, created_at") \
            .eq("chat_id", chat_id) \
            .order("created_at", desc=False) \
            .execute()
        msgs = resp.data if resp.data else []
        new_msgs: List[Dict] = []
        for m in msgs:
            role = m.get("role", "GemFlow")
            content = m.get("content", "")
            new_msgs.append({"role": role, "content": content})
        st.session_state.messages = new_msgs
        st.session_state.chat_id = chat_id
        return True, "Loaded chat"
    except Exception as e:
        return False, f"Failed to load: {e}"

def fetch_user_chats():
    if not st.session_state.user:
        return []
    try:
        user_id = st.session_state.user["id"]
        client = _get_supabase_client_for_frontend()
        resp = client.table("chats") \
            .select("id, title, created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .execute()
        chats = resp.data if resp.data else []
        st.session_state.chats = chats
        return chats
    except Exception:
        return st.session_state.chats

header_col, _ = st.columns([7, 1])
with header_col:
    st.title("GemFlow")
    st.subheader("AI Chat — simple, private, and instant")

col_main, col_side = st.columns([3, 1])

with col_main:
    chat_area = st.container()
    with chat_area:
        if not st.session_state.messages:
            st.info("Start the conversation by typing a message below.")
        for m in st.session_state.messages:
            if m["role"] == "user":
                st.markdown(f"**You:** {m['content']}")
            else:
                st.markdown(f"**GemFlow:** {m['content']}")

        st.write("---")

        with st.form("message_form", clear_on_submit=True):
            user_input = st.text_input("Type your message", placeholder="Ask anything...", key="msg_input")
            submitted = st.form_submit_button("Send")
            if submitted and user_input:
                append_message("user", user_input)
                with st.spinner("GemFlow is thinking..."):
                    reply, chat_id = call_backend_send(user_input)
                append_message("GemFlow", reply)
                if chat_id:
                    st.session_state.chat_id = chat_id
                st.rerun()

with col_side:
    if st.session_state.user:
        st.sidebar.write(f"Logged in as: **{st.session_state.user.get('email','user')}**")
        if st.sidebar.button("Log out"):
            try:
                sb.sign_out()
            except Exception:
                pass
            st.session_state.user = None
            st.session_state.chats = []
            st.rerun()

        st.sidebar.divider()
        st.sidebar.subheader("Your chats")
        chats = fetch_user_chats()
        if chats:
            options = {c['title'] if 'title' in c and c['title'] else c['id']: c['id'] for c in chats}
            choice = st.sidebar.selectbox("Open chat", options.keys())
            if st.sidebar.button("Load selected chat"):
                selected_id = options[choice]
                ok, msg = load_chat_by_id(selected_id)
                if ok:
                    st.sidebar.success(msg)
                else:
                    st.sidebar.error(msg)
                st.rerun()
        else:
            st.sidebar.info("No saved chats found.")

    else:
        st.sidebar.write("To save chats, sign up or log in.")
        with st.sidebar.expander("Sign up / Log in"):
            tab1, tab2 = st.tabs(["Log in", "Sign up"])
            with tab1:
                li_email = st.text_input("Email", key="li_email")
                li_pass = st.text_input("Password", type="password", key="li_pass")
                if st.button("Log in", key="btn_login"):
                    try:
                        res = sb.sign_in(li_email, li_pass)
                        access_token = None
                        if hasattr(res, "session") and res.session:
                            access_token = getattr(res.session, "access_token", None)
                        elif isinstance(res, dict):
                            session = res.get("session")
                            if session:
                                access_token = session.get("access_token")

                        user_id = None
                        user_email = None
                        if hasattr(res, "user") and res.user:
                            user_id = getattr(res.user, "id", None)
                            user_email = getattr(res.user, "email", None)
                        elif isinstance(res, dict):
                            user = res.get("user")
                            if user:
                                user_id = user.get("id")
                                user_email = user.get("email")

                        if user_id:
                            st.session_state.user = {
                                "id": user_id,
                                "email": user_email,
                                "access_token": access_token,
                            }
                            st.success("Logged in")
                            st.rerun()
                        else:
                            st.error("Login failed: could not parse user info")
                    except Exception as e:
                        st.error(f"Login failed: {e}")
            with tab2:
                su_email = st.text_input("Email (signup)", key="su_email")
                su_pass = st.text_input("Password", type="password", key="su_pass")
                if st.button("Sign up", key="btn_signup"):
                    try:
                        res = sb.sign_up(su_email, su_pass)
                        err = getattr(res, "error", None) or (res.get("error") if isinstance(res, dict) else None)
                        if err:
                            st.error(f"Signup error: {err}")
                        else:
                            st.success("Signup successful — please log in")
                    except Exception as e:
                        st.error(f"Signup failed: {e}")

    st.sidebar.divider()
    st.sidebar.subheader("Previous Chats:")

    st.sidebar.divider()

    if st.sidebar.button("Clear chats"):
        st.session_state.messages = []
        st.session_state.chat_id = None
        st.rerun()
