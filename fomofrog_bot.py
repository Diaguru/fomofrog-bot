# fomofrog_bot.py (Postgres version)
import os
import time
import asyncio
import io
from decimal import Decimal

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from web3 import Web3
from web3.middleware import geth_poa_middleware

from uniswap_parser import analyze_tx_for_purchase
from card_template import make_image_card
from postgres_client import PostgresClient

# ---- Config from ENV ----
RPC_URL = os.getenv("RPC_URL", "https://base.publicnode.com")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
TOKEN_ADDRESS = os.getenv("TOKEN_ADDRESS", "0xe509B5232AbCa3c7f15672366ceAFF8E7285bA50")
MIN_TOKEN_AMOUNT = Decimal(os.getenv("MIN_TOKEN_AMOUNT", "1"))
RUN_POLL = os.getenv("RUN_POLL", "false").lower() in ("1","true","yes")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "6"))

if not DISCORD_BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is required in env")

# Web3 init
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Postgres client
pg_client = PostgresClient()
pg_client.ensure_table()

# Discord bot init
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# send embed/file via webhook
async def send_to_discord_webhook(webhook_url, title, description, file_bytes=None, filename="card.png"):
    payload = {"username":"FomoFrog Verify","embeds":[{"title":title,"description":description,"timestamp":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}]}
    async with aiohttp.ClientSession() as session:
        if file_bytes:
            data = aiohttp.FormData()
            data.add_field("payload_json", value=__import__("json").dumps(payload), content_type="application/json")
            data.add_field("file", file_bytes, filename=filename, content_type="image/png")
            async with session.post(webhook_url, data=data) as resp:
                text = await resp.text()
                if resp.status not in (200,204):
                    print("Webhook upload error", resp.status, text)
        else:
            async with session.post(webhook_url, json=payload) as resp:
                text = await resp.text()
                if resp.status not in (200,204):
                    print("Webhook error", resp.status, text)

# Manual verify + notify
async def manual_verify_and_notify(txhash, destination_webhook=None):
    destination_webhook = destination_webhook or DISCORD_WEBHOOK
    if not destination_webhook:
        print("No DISCORD_WEBHOOK set — skipping notify")
    try:
        res = analyze_tx_for_purchase(w3, txhash, Web3.toChecksumAddress(TOKEN_ADDRESS), MIN_TOKEN_AMOUNT)
    except Exception as e:
        print("analyze error:", e)
        res = None

    if not res:
        if destination_webhook:
            await send_to_discord_webhook(destination_webhook, "Verification Failed ❌", f"Tx `{txhash}` did not qualify.")
        return False

    # Save to Postgres
    try:
        pg_client.insert_purchase(txhash=res["txhash"], buyer=res.get("buyer"), amount=res["amount"])
    except Exception as e:
        print("Postgres insert error:", e)

    # make image card
    try:
        buf = make_image_card(res.get("buyer") or "unknown", res["amount"], res["txhash"])
        buf.seek(0)
        file_bytes = buf.read()
    except Exception as e:
        print("card generation error:", e)
        file_bytes = None

    # send notification
    if destination_webhook:
        desc = f"Buyer: `{res.get('buyer')}`\nAmount: `{res['amount']}`\nTx: `{res['txhash']}`"
        await send_to_discord_webhook(destination_webhook, "Purchase Verified ✅", desc, file_bytes=file_bytes)

    return True

# Slash command /verify
@tree.command(name="verify", description="Verify a Uniswap purchase txhash")
@app_commands.describe(txhash="Transaction hash (0x...)")
async def verify(interaction: discord.Interaction, txhash: str):
    await interaction.response.defer()
    ok = await manual_verify_and_notify(txhash)
    if ok:
        await interaction.followup.send(f"✅ Verification submitted for `{txhash}`")
    else:
        await interaction.followup.send(f"❌ Could not verify `{txhash}`")

# Slash command /rank
@tree.command(name="rank", description="Show top buyers")
@app_commands.describe(limit="Number of top buyers")
async def rank(interaction: discord.Interaction, limit: int = 10):
    await interaction.response.defer()
    rows = pg_client.top_buyers(limit)
    if not rows:
        await interaction.followup.send("No purchases yet.")
        return
    msg = "\n".join([f"{i+1}. `{r['buyer']}` — {r['total']}" for i, r in enumerate(rows)])
    await interaction.followup.send(f"🏆 Top Buyers:\n{msg}")

# simple ping
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("pong 🐸")

@bot.event
async def on_ready():
    try:
        await tree.sync()
        print("Commands synced")
    except Exception as e:
        print("Command sync error", e)
    print(f"Logged in as {bot.user}")

# Optional polling loop: auto verify
async def polling_loop():
    print("Starting polling loop...")
    processed = set()
    while True:
        try:
            latest = w3.eth.block_number
            block = w3.eth.get_block(latest, full_transactions=True)
            for tx in block.transactions:
                txhash = tx.hash.hex()
                if txhash in processed:
                    continue
                try:
                    found = analyze_tx_for_purchase(w3, txhash, Web3.toChecksumAddress(TOKEN_ADDRESS), MIN_TOKEN_AMOUNT)
                    if found:
                        await manual_verify_and_notify(txhash)
                        processed.add(txhash)
                except Exception as e:
                    print("Error analyzing tx", txhash, e)
            await asyncio.sleep(POLL_INTERVAL)
        except Exception as e:
            print("Polling error:", e)
            await asyncio.sleep(3)

if __name__ == "__main__":
    if RUN_POLL:
        loop = asyncio.get_event_loop()
        loop.create_task(polling_loop())
        bot.run(DISCORD_BOT_TOKEN)
    else:
        bot.run(DISCORD_BOT_TOKEN)
