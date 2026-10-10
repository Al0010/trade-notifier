# Real-Time TradingView to Telegram Notifier 

A high-performance, real-time notification system that instantly forwards TradingView alerts to Telegram via **Supabase Edge Functions** and **Database Webhooks**, replacing high-latency polling methods.

Messages are delivered in **under a second** right when a new trade is recorded in your database.

## Architecture Overview

1. **TradingView** sends a webhook or alert payload into your Supabase database (`your_trades_table` table).
2. Supabase **Database Webhook** listens for `INSERT` events on the `your_trades_table` table in real-time.
3. The webhook triggers a serverless **Supabase Edge Function** (written in TypeScript/Deno).
4. The Edge Function fetches additional strategy metrics if needed, formats the message, and instantly dispatches it to your **Telegram** chat/channel.

---

## Step-by-Step Setup Guide

### Phase 1: Create the Supabase Edge Function

1. Go to your **Supabase Dashboard**.
2. Click on **Edge Functions** in the left sidebar.
3. Create a new function named `telegram-notifier`.
4. Paste the TypeScript code into the editor and deploy

---

### Phase 2: Configure Environment Secrets

In your Supabase Dashboard, go to **Project Settings** -> **Edge Functions** -> **Secrets** and add the following keys:

* `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API Token (obtained via [@BotFather](https://t.me/BotFather)).
* `TELEGRAM_CHAT_ID`: Your target Telegram Chat or Channel ID.

*(Note: `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are injected automatically by Supabase).*

---

### Phase 3: Connect via Database Webhook

1. Go to **Database** -> **Webhooks** in your Supabase dashboard.
2. Click **Create a new webhook** with these settings:
   * **Name:** `send_telegram_trade`
   * **Table:** `public your_trades_table`
   * **Events:** Check **Insert**
   * **Type of webhook:** Select **Supabase Edge Functions**
   * **Edge Function:** Select `telegram-notifier`
3. Save the webhook.

---

## Testing the System

You can test the real-time notification loop by executing a manual test insert in your **SQL Editor**:

```sql
INSERT INTO your_trades_table (
    strategy_id,
    ticker,
    type_order,
    status,
    tv_timestamp,
    pnl,
    equity_after
) VALUES (
    'YOUR_TARGET_STRATEGY_UUID_HERE',
    'BTCUSDC',
    'buy',
    'closed',
    extract(epoch from now()) * 1000,
    150.50,
    10150.50
);
```

Check your Telegram channel—the update will arrive instantly!
