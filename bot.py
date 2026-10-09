import os
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import requests

# Carica le variabili d'ambiente dal file .env o dai Secrets di GitHub
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Errore: SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY mancanti nelle variabili d'ambiente")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TARGET_STRATEGY = "c4b90f35-c965-48f8-86c1-7e45257bb34a"

def fetch_strategy_metrics(strategy_id):
    """Recupera zscore_streaks e run_up_efficiency_pct dalla tabella forward_strategies"""
    try:
        response = supabase.table("forward_strategies") \
            .select("zscore_streaks, run_up_efficiency_pct") \
            .eq("id", strategy_id) \
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        print(f"Errore nel recupero delle metriche della strategia: {e}")
    return {}

def format_unix_timestamp(ts):
    """Converte un timestamp UNIX in una stringa di data/ora leggibile"""
    try:
        if isinstance(ts, (int, float)) and ts > 1e11:
            ts = ts / 1000.0
        return datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(ts)

def send_telegram_message(trade_data):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    strategy_id = trade_data.get('strategy_id')
    if strategy_id and strategy_id != TARGET_STRATEGY:
        return

    ticker = trade_data.get('ticker', 'BTCUSDC')
    type_order = trade_data.get('type_order', 'N/D')
    status = trade_data.get('status', 'N/D')
    raw_timestamp = trade_data.get('tv_timestamp', 'N/D')
    tv_timestamp = format_unix_timestamp(raw_timestamp)
    
    pnl = trade_data.get('pnl')
    equity_after = trade_data.get('equity_after')
    
    strategy_metrics = {}
    if status == 'closed' and strategy_id:
        strategy_metrics = fetch_strategy_metrics(strategy_id)

    zscore_streaks = strategy_metrics.get('zscore_streaks', 'N/D')
    run_up_efficiency = strategy_metrics.get('run_up_efficiency_pct', 'N/D')

    if status == 'closed':
        status_emoji = "🔴"
        pnl_text = f"\n💵 **PnL:** `{pnl}`" if pnl is not None else ""
        equity_text = f"\n🏦 **Equity Post-Trade:** `{equity_after}`" if equity_after is not None else ""
        
        closed_details = (
            f"{pnl_text}"
            f"{equity_text}\n"
            f"⚡ **Z-Score Streaks:** `{zscore_streaks}`\n"
            f"🎯 **Run-up Efficiency:** `{run_up_efficiency}%`"
        )
    else:
        status_emoji = "🟢"
        closed_details = ""

    message = (
        f"🚨 **Aggiornamento Trade ({ticker})**\n\n"
        f"📊 **Asset:** {ticker}\n"
        f"🔄 **Tipo Ordine:** `{type_order.upper()}`\n"
        f"📌 **Stato:** {status_emoji} `{status}`"
        f"{closed_details}\n\n"
        f"🕒 **Timestamp TV:** {tv_timestamp}"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            print(f"Messaggio Telegram inviato con successo per il trade {trade_data.get('id')}!")
        else:
            print(f"Errore Telegram ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"Eccezione nell'invio del messaggio Telegram: {e}")

def main():
    print("Controllo nuovi trade (GitHub Actions - Esecuzione singola)...")
    
    # Calcoliamo il timestamp di 3 minuti fa in millisecondi (copre l'intervallo del cron)
    three_minutes_ago = int((time.time() - 180) * 1000)
    
    try:
        # Interroghiamo Supabase filtrando per la strategia specifica e i timestamp recenti
        response = supabase.table("forward_trades") \
            .select("*") \
            .eq("strategy_id", TARGET_STRATEGY) \
            .gt("tv_timestamp", three_minutes_ago) \
            .order("tv_timestamp", desc=False) \
            .execute()
            
        if response.data:
            print(f"Trovati {len(response.data)} nuovi trade da elaborare.")
            for trade in response.data:
                send_telegram_message(trade)
        else:
            print("Nessun nuovo trade recente.")
            
    except Exception as e:
        print(f"Errore durante il controllo dei trade: {e}")

if __name__ == "__main__":
    main()
