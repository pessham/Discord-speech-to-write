import os
import json
import logging
from pathlib import Path

import discord
from discord import File, Interaction
from discord.ext import commands

from utils.speech import transcribe
from utils.summarize import summarize
from utils.obsidian import save_and_link

logging.basicConfig(level=logging.INFO)

# Prefer environment variables (Railway) and fall back to local config.json for dev
TOKEN = os.getenv("DISCORD_TOKEN")
VAULT_PATH_STR = os.getenv("VAULT_PATH")
if not TOKEN or not VAULT_PATH_STR:
    try:
        _cfg = json.load(open("config.json"))
        TOKEN = TOKEN or _cfg.get("discord_token")
        VAULT_PATH_STR = VAULT_PATH_STR or _cfg.get("vault_path")
    except FileNotFoundError:
        raise RuntimeError("DISCORD_TOKEN/VAULT_PATH env vars not set and config.json not found")
VAULT_PATH = Path(VAULT_PATH_STR)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)


audio_extensions = {".wav", ".mp3", ".m4a", ".ogg", ".oga", ".webm"}


@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")


async def _process_attachment(channel, attachment, original_author):
    if Path(attachment.filename).suffix.lower() not in audio_extensions:
        return False
    tmp = Path("temp"); tmp.mkdir(exist_ok=True)
    file_path = tmp / attachment.filename
    await attachment.save(file_path)
    await channel.send("文字起こし中…")
    transcript = transcribe(file_path)
    await channel.send("要約中…")
    parts = summarize(transcript)
    md_content = f"**書き起こし**\n\n{transcript}\n\n---\n\n{parts['summary']}\n"
    md_filename = save_and_link(VAULT_PATH, attachment.filename.split(".")[0], md_content)
    # separate messages
    await channel.send(transcript)
    await channel.send(f"{parts['summary']}\n\n{parts['x']}")
    await channel.send(f"Obsidian: {md_filename}")
    return True

@bot.command(name="transcribe")
async def _transcribe(ctx: commands.Context):
    if not ctx.message.attachments:
        await ctx.send("音声ファイルを添付してください。")
        return
    await _process_attachment(ctx, ctx.message.attachments[0], ctx.author)


@bot.event
async def on_message(message: discord.Message):
    # skip own messages and commands (starting with /)
    if message.author.bot:
        return
    if message.content.startswith("/transcribe"):
        await bot.process_commands(message)
        return
    # auto process first audio attachment if present
    if message.attachments:
        processed = await _process_attachment(message.channel, message.attachments[0], message.author)
        if processed:
            return
    await bot.process_commands(message)

@bot.command(name="post")
async def _post(ctx: commands.Context, target: str):
    """ダミー: 今は投稿せず確認用。target=x|note"""
    await ctx.send(f"{target} に投稿（ダミー）: 実装待ち")


if __name__ == "__main__":
    bot.run(TOKEN)
