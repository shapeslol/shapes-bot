"""Your first Yapper bot in Python. Nothing to install (standard library only). Python 3.9+.

  1. Save yapper.py next to this file: https://www.yapper.website/sdk/yapper.py
  2. Put your token below (Settings -> Developer -> Create).
  3. Add the bot to a server you manage (same place), then run:  python starter.py
"""
import os
import random

try:
    import yapper
except ImportError:
    raise SystemExit("Save yapper.py next to this file first: https://www.yapper.website/sdk/yapper.py")

bot = yapper.Bot(os.environ.get("YAPPER_BOT_TOKEN") or "PASTE_YOUR_TOKEN_HERE")


@bot.command("ping", "Is the bot alive?")
def ping(msg):
    msg.reply("pong 🏓")


@bot.command("roll", "Roll a die, like /roll 20")
def roll(msg):
    first = msg.argv[0] if msg.argv else "6"
    sides = max(2, min(1000, int(first) if first.isascii() and first.isdigit() else 6))
    msg.reply(f"🎲 {random.randint(1, sides)} (d{sides})")


@bot.on("message")
def mentioned(msg):
    if msg.mentioned:
        msg.reply(f"hey {msg.author_mention}, try /ping")


@bot.on("member_join")
def welcome(ev):
    text = bot.channels(ev.server_id, type="text")
    if text:
        bot.send(text[0].id, f"welcome <@{ev.user_id}>! you're member #{ev.member_count}")


# More commands in other files? Put them in a cogs folder and uncomment:
# bot.load_extensions("cogs")

bot.run()
