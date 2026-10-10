# Real-Time TradingView to Telegram Notifier 🚀

A high-performance, real-time notification system that instantly forwards TradingView alerts to Telegram via **Supabase Edge Functions** and **Database Webhooks**, replacing high-latency polling methods (such as GitHub Actions).

Messages are delivered in **under a second** right when a new trade is recorded in your database.

## 🏗️ Architecture Overview

1. **TradingView** sends a webhook or alert payload into your Supabase database (`forward_trades` table).
2. Supabase **Database Webhook** listens for `INSERT` events on the `forward_trades` table in real-time.
3. The webhook triggers a serverless **Supabase Edge Function** (written in TypeScript/Deno).
4. The Edge Function fetches additional strategy metrics if needed, formats the message, and instantly dispatches it to your **Telegram** chat/channel.

---

## 🛠️ Step-by-Step Setup Guide

### Phase 1: Create the Supabase Edge Function

1. Go to your **Supabase Dashboard**.
2. Click on **Edge Functions** in the left sidebar.
3. Create a new function named `telegram-notifier`.
4. Paste the following TypeScript code into the editor and deploy:

```typescript
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// Replace with your specific Target Strategy UUID or remove if you want all strategies
const TARGET_STRATEGY = "YOUR_TARGET_STRATEGY_UUID_HERE";

function formatUnixTimestamp(ts: any): string {
  try {
    let num = Number(ts);
    if (num > 1e11) {
      num = num / 1000.0;
    }
    const date = new Date(num * 1000);
    return date.toISOString().replace('T', ' ').substring(0, 19);
  } catch {
    return String(ts);
  }
}

Deno.serve(async (req) => {
  try {
    const payload = await req.json();
    const tradeData = payload.record;
    if (!tradeData) {
      return new Response(JSON.stringify({ error: "No record found in payload" }), { status: 400 });
    }

    const strategyId = tradeData.strategy_id;
    if (TARGET_STRATEGY && strategyId && strategyId !== TARGET_STRATEGY) {
      return new Response(JSON.stringify({ message: "Strategy ignored" }), { status: 200 });
    }

    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const telegramToken = Deno.env.get('TELEGRAM_BOT_TOKEN');
    const chatId = Deno.env.get('TELEGRAM_CHAT_ID');

    const ticker = tradeData.ticker || 'BTCUSDC';
    const typeOrder = tradeData.type_order || 'N/D';
    const status = tradeData.status || 'N/D';
    const rawTimestamp = tradeData.tv_timestamp || 'N/D';
    const tvTimestamp = formatUnixTimestamp(rawTimestamp);
    
    const pnl = tradeData.pnl;
    const equityAfter = tradeData.equity_after;

    let zscoreStreaks = 'N/D';
    let runUpEfficiency = 'N/D';

    if (status === 'closed' && strategyId) {
      const { data: stratData } = await supabase
        .table("forward_strategies")
        .select("zscore_streaks, run_up_efficiency_pct")
        .eq("id", strategyId)
        .single();
      
      if (stratData) {
        zscoreStreaks = stratData.zscore_streaks ?? 'N/D';
        runUpEfficiency = stratData.run_up_efficiency_pct ?? 'N/D';
      }
    }

    let statusEmoji = "🟢";
    let closedDetails = "";

    if (status === 'closed') {
      statusEmoji = "🔴";
      const pnlText = pnl !== null && pnl !== undefined ? `\n💵 **PnL:** \`${pnl}\`` : "";
      const equityText = equityAfter !== null && equityAfter !== undefined ? `\n🏦 **Equity Post-Trade:** \`${equityAfter}\`` : "";
      
      closedDetails = (
        `${pnlText}` +
        `${equityText}\n` +
        `⚡ **Z-Score Streaks:** \`${zscoreStreaks}\`\n` +
        `🎯 **Run-up Efficiency:** \`${runUpEfficiency}%\``
      );
    }

    const message = (
      `🚨 **Trade Update (${ticker})**\n\n` +
      `📊 **Asset:** ${ticker}\n` +
      `🔄 **Order Type:** \`${type_order.toUpperCase()}\`\n` +
      `📌 **Status:** ${statusEmoji} \`${status}\`` +
      `${closedDetails}\n\n` +
      `🕒 **TV Timestamp:** ${tvTimestamp}`
    );

    const telegramUrl = `https://api.telegram.org/bot${telegramToken}/sendMessage`;
    const tgRes = await fetch(telegramUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text: message,
        parse_mode: "Markdown"
      })
    });

    const tgResultText = await tgRes.text();
    if (!tgRes.ok) {
      console.error("Telegram error:", tgResultText);
      return new Response(JSON.stringify({ error: tgResultText }), { status: 500 });
    }

    return new Response(JSON.stringify({ success: true, message: "Message sent successfully!" }), { status: 200 });

  } catch (err) {
    console.error(err);
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
});
```

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
   * **Table:** `public forward_trades`
   * **Events:** Check **Insert**
   * **Type of webhook:** Select **Supabase Edge Functions**
   * **Edge Function:** Select `telegram-notifier`
3. Save the webhook.

---

## 🧪 Testing the System

You can test the real-time notification loop by executing a manual test insert in your **SQL Editor**:

```sql
INSERT INTO forward_trades (
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
