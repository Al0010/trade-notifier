import os
import time
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def send_telegram_message(trade):
    # Personalizza qui il messaggio da mandare ai tuoi utenti FREE su Telegram
    message = f"🚨 *Signal FREE*\nID: {trade.get('id')}\nDettagli trade in arrivo..."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

def main():
    print("Controllo nuovi trade (Modalità GitHub Actions)...")
    
    # Calcoliamo il timestamp di 3 minuti fa in millisecondi (copre l'intervallo tra un'esecuzione e l'altra)
    three_minutes_ago = int((time.time() - 180) * 1000)
    
    try:
        # Cerchiamo i trade recenti non ancora inviati
        response = supabase.table("forward_trades") \
            .select("*") \
            .gt("tv_timestamp", three_minutes_ago) \
            .order("tv_timestamp", desc=False) \
            .execute()
            
        if response.data:
            for trade in response.data:
                trade_id = trade.get('id')
                print(f"🚀 Invio trade FREE: {trade_id}")
                send_telegram_message(trade)
        else:
            print("Nessun nuovo trade recente.")
            
    except Exception as e:
        print(f"Errore durante il controllo: {e}")

if __name__ == "__main__":
    main()
