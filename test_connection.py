from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

url = "https://tsxbwnfmjudhopmedymw.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzeGJ3bmZtanVkaG9wbWVkeW13Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxMDY1NzcsImV4cCI6MjA4NDY4MjU3N30.FyGligq5PRse4KMyeEyiMvAbImd7nS9ucBGYoS6pooU"

print("Testing Supabase connection...")
print(f"URL: {url}")
print(f"Key: {key[:50]}...")
print()

try:
    supabase = create_client(url, key)
    print("✅ Client created!")
    
    # Test database
    result = supabase.table('products').select("*").limit(1).execute()
    print("✅ Database connected!")
    print(f"Products in database: {len(result.data)}")
    
    # Test storage
    buckets = supabase.storage.list_buckets()
    print(f"✅ Storage connected!")
    print(f"Buckets found: {[b['name'] for b in buckets]}")
    
    print("\n🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()