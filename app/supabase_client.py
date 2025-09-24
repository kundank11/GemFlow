import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def test_connection():
    res = supabase.table("chats").select("*").limit(1).execute()
    print("Supabase connected! Rows:", res.data)

if __name__ == "__main__":
    test_connection()
