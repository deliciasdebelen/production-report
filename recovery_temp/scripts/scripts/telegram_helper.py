import os
import sys
import requests

# Ensure we can import config from current dir
sys.path.append(os.path.dirname(__file__))

try:
    import config
except ImportError:
    config = None

def send_message(text):
    if not config:
        print("[Telegram] Error: config.py not found.")
        return

    token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')
    
    # Check for placeholders or empty
    if not token or "REPLACE" in token or not chat_id or "REPLACE" in str(chat_id):
        print("[Telegram] Warning: Credentials not set in scripts/config.py")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "Markdown"
    }

    try:
        # print(f"[Telegram] Sending message to {chat_id}...")
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            print("[Telegram] Message sent successfully.")
        else:
            print(f"[Telegram] Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")
