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
