import streamlit as st
from supabase import create_client

def _get_client():
    url = st.secrets.get("SUPABASE_URL")
    anon = st.secrets.get("SUPABASE_ANON_KEY")
    if not url or not anon:
        raise RuntimeError("Supabase secrets not set in frontend/.streamlit/secrets.toml")
    return create_client(url, anon)

def sign_up(email: str, password: str):
    client = _get_client()
    return client.auth.sign_up({"email": email, "password": password})

def sign_in(email: str, password: str):
    client = _get_client()
    return client.auth.sign_in_with_password({"email": email, "password": password})

def get_user():
    client = _get_client()
    return client.auth.get_user()

def get_session():
    client = _get_client()
    return client.auth.get_session()

def sign_out():
    client = _get_client()
    return client.auth.sign_out()
