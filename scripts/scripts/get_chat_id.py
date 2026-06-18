import requests
import time

def get_id():
    print("--- Telegram Setup Helper ---")
    token = input("1. Enter your Bot Token (from @BotFather): ").strip()
    if not token: 
        print("Token is required.")
        return
    
    print("\n2. Please send a message (e.g., 'HELLO') to your bot in the Telegram Group you created.")
    print("   Make sure the bot has been added to the group!")
    input("Press Enter after you have sent the message...")
    
    print("Checking for updates...")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        res = requests.get(url).json()
        if not res.get('ok'):
            print(f"Error connecting to Telegram: {res}")
            return
            
        updates = res.get('result', [])
        if not updates:
            print("No new messages found. Please ensure:")
            print(" - The bot is in the group.")
            print(" - You sent a message *after* adding the bot.")
            print(" - You might need to remove and re-add the bot if privacy settings prevent it from seeing messages.")
        else:
            # Find the last message (group or private)
            last_update = updates[-1]
            chat = last_update.get('message', {}).get('chat', {})
            
            chat_id = chat.get('id')
            title = chat.get('title', 'Private Chat')
            type_ = chat.get('type')
            
            print(f"\n✅ SUCCESS! Metadata Found:")
            print(f"   Chat Title: {title}")
            print(f"   Chat Type:  {type_}")
            print(f"   CHAT ID:    {chat_id}")
            print("\n>>> COPY THIS ID INTO scripts/config.py <<<")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    get_id()
