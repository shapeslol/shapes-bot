import os
import sys
import threading
import time
import json
import signal
import asyncio
import discord
import aiohttp
import pytz
import numbers
#import pandas as pd # Last resort if i keep getting json errors
from slpp import slpp as lua
from pickledb import PickleDB
from datetime import datetime, timezone
from discord import app_commands
import requests
from discord.ext import commands
from discord.gateway import DiscordWebSocket, _log
from discord.ext.commands import Bot
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from flask_cors import CORS
import base64
import urllib

#=== Database Setup ===
countingDB = PickleDB('counting.db')
embedDB = PickleDB('embed.db')
usersDB = PickleDB('users.db')

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
owner = "sl.ip"
co_owner = "<@481295611417853982>"
MainURL = "https://shapes.lol"
searchengine = "621a38269031b4e89" # PLEASE USE YOUR OWN SERACH ENGINE ID FROM https://cse.google.com/

# get the bot token from TOKEN.txt
try:
    with open('TOKEN.txt', 'r') as f:
        token = f.read()
except FileNotFoundError:
    print("Error: The file 'TOKEN.txt' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")

# get the admin key from akey.txt
try:
    with open('akey.txt', 'r') as f:
        ADMIN_KEY = f.read()
except FileNotFoundError:
    print("Error: The file 'akey.txt' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")

# get the google API key from GoogleToken.txt
try:
    with open('GoogleToken.txt', 'r') as f:
        GoogleAPIKey = f.read()
except FileNotFoundError:
    print("Error: The file 'GoogleToken.txt' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")

# === Flask App Setup ===
app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "keepthisasecret")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bot Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1e1e2f; color: #fff; padding: 20px; }
        h1 { color: #50fa7b; }
        select, input[type=text] { padding: 6px; border-radius: 5px; border: none; margin: 5px 0; }
        input[type=submit] { background: #50fa7b; border: none; padding: 8px 12px; border-radius: 5px; color: #000; cursor: pointer; }
        .server { background: #282a36; padding: 10px; margin-bottom: 15px; border-radius: 10px; }
        .logout { margin-top: 20px; }
        .presence-button {
            display: inline-block;
            margin-top: 10px;
            background-color: #7289da;
            color: white;
            padding: 10px 18px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            transition: background-color 0.3s ease;
        }
        .presence-button:hover {
            background-color: #5b6eae;
        }
    </style>
</head>
<body>
    <h1>🤖 Bot Dashboard</h1>
    <p>Status: <b style="color:lime;">Online</b></p>
    <p>Connected to {{ guilds|length }} {{ 'server' if guilds|length == 1 else 'servers' }}</p>
    
    <!-- Presence Button -->
    <a href="https://shapes.lol/discord" target="_blank" rel="noopener" class="presence-button">
        Join Our Server
    </a>
    
    {% for g in guilds %}
        <div class="server">
            <h3>{{ g.name }}</h3>
            <form action="/send" method="post">
                <input type="hidden" name="guild_id" value="{{ g.id }}">
                <label for="channel">Channel:</label>
                <select name="channel_id">
                    {% for c in g.text_channels %}
                        <option value="{{ c.id }}">{{ c.name }}</option>
                    {% endfor %}
                </select>
                <br>
                <label for="message">Message:</label>
                <input type="text" name="message" placeholder="Enter your message" required>
                <br>
                <input type="submit" value="Send">
            </form>
        </div>
    {% endfor %}
    <div class="logout">
        <a href="/logout" style="color: #ff5555;">Logout</a>
    </div>
</body>
</html>
"""

# === Admin Auth Decorator ===
def admin_required(f):
    def wrapped(*args, **kwargs):
        if session.get("admin") != True:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    wrapped.__name__ = f.__name__
    return wrapped

# === Flask Routes ===
@app.route("/status")
def status():
    return "OK", 200

@app.route("/activity")
def activity():
    return redirect(url_for("admin_login"))

@app.route("/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin") == True:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        key = request.form.get("key")
        if key == ADMIN_KEY:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        else:
            return '''
                <h3 style="color: red; font-family: Arial, sans-serif;">Incorrect key.</h3>
                <a href="/login" style="font-family: Arial, sans-serif; color: #50fa7b;">Try again</a>
            '''

    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login</title>
        <style>
            body {
                background: #121212;
                color: #eee;
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .login-container {
                background: #282a36;
                padding: 40px 50px;
                border-radius: 12px;
                box-shadow: 0 0 15px #50fa7b;
                text-align: center;
                width: 320px;
            }
            h2 {
                margin-bottom: 25px;
                color: #50fa7b;
            }
            input[type=password] {
                width: 100%;
                padding: 12px;
                margin-bottom: 20px;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                background: #44475a;
                color: #f8f8f2;
            }
            input[type=password]::placeholder {
                color: #bd93f9;
            }
            button {
                background: #50fa7b;
                border: none;
                color: #000;
                padding: 12px 0;
                width: 100%;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
                cursor: pointer;
                transition: background 0.3s ease;
            }
            button:hover {
                background: #44d366;
            }
            a {
                display: inline-block;
                margin-top: 15px;
                color: #50fa7b;
                text-decoration: none;
                font-size: 14px;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h2>Admin Login</h2>
            <form method="POST">
                <input type="password" name="key" placeholder="Enter admin key" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route("/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

# Dashboard at root /
@app.route("/", methods=["GET"])
@admin_required
def dashboard():
    if not bot_ready:
        return "<h3>Bot is not ready yet, please try again in a moment.</h3>"
    return render_template_string(HTML_TEMPLATE, guilds=cached_guilds)

# Redirect /activity to /
@app.route("/activity")
def activity_redirect():
    return redirect(url_for("dashboard"))

@app.route("/send", methods=["POST"])
@admin_required
def send_message():
    guild_id = int(request.form["guild_id"])
    channel_id = int(request.form["channel_id"])
    message = request.form["message"]

    guild = discord.utils.get(bot.guilds, id=guild_id)
    if guild:
        channel = discord.utils.get(guild.text_channels, id=channel_id)
        if channel:
            try:
                bot.loop.create_task(channel.send(message))
            except Exception as e:
                print(f"Failed to send message: {e}")

    return redirect(url_for("dashboard"))

# === Globals for caching and ready state ===
cached_guilds = []
bot_ready = False

class MyGateway(DiscordWebSocket):

    async def identify(self):
        payload = {
            'op': self.IDENTIFY,
            'd': {
                'token': token,
                'properties': {
                    '$os': sys.platform,
                    '$browser': 'Discord Android',
                    '$device': 'Discord Android',
                    '$referrer': '',
                    '$referring_domain': ''
                },
                'compress': True,
                'large_threshold': 250,
                'v': 3
            }
        }

        if self.shard_id is not None and self.shard_count is not None:
            payload['d']['shard'] = [self.shard_id, self.shard_count]

        state = self._connection
        if state._activity is not None or state._status is not None:
            payload['d']['presence'] = {
                'status': state._status,
                'game': state._activity,
                'since': 0,
                'afk': False
            }

        if state._intents is not None:
            payload['d']['intents'] = state._intents.value

        await self.call_hooks('before_identify', self.shard_id, initial=self._initial_identify)
        await self.send_as_json(payload)
        _log.info('Shard ID %s has sent the IDENTIFY payload.', self.shard_id)


class MyBot(Bot):

    async def connect(self, *, reconnect: bool = True) -> None:
        """|coro|

        Creates a websocket connection and lets the websocket listen
        to messages from Discord. This is a loop that runs the entire
        event system and miscellaneous aspects of the library. Control
        is not resumed until the WebSocket connection is terminated.

        Parameters
        -----------
        reconnect: :class:`bool`
            If we should attempt reconnecting, either due to internet
            failure or a specific failure on Discord's part. Certain
            disconnects that lead to bad state will not be handled (such as
            invalid sharding payloads or bad tokens).

        Raises
        -------
        :exc:`.GatewayNotFound`
            If the gateway to connect to Discord is not found. Usually if this
            is thrown then there is a Discord API outage.
        :exc:`.ConnectionClosed`
            The websocket connection has been terminated.
        """

        backoff = discord.client.ExponentialBackoff()
        ws_params = {
            'initial': True,
            'shard_id': self.shard_id,
        }
        while not self.is_closed():
            try:
                coro = MyGateway.from_client(self, **ws_params)
                self.ws = await asyncio.wait_for(coro, timeout=60.0)
                ws_params['initial'] = False
                while True:
                    await self.ws.poll_event()
            except discord.client.ReconnectWebSocket as e:
                _log.info('Got a request to %s the websocket.', e.op)
                self.dispatch('disconnect')
                ws_params.update(sequence=self.ws.sequence, resume=e.resume, session=self.ws.session_id)
                continue
            except (OSError,
                    discord.HTTPException,
                    discord.GatewayNotFound,
                    discord.ConnectionClosed,
                    aiohttp.ClientError,
                    asyncio.TimeoutError) as exc:

                self.dispatch('disconnect')
                if not reconnect:
                    await self.close()
                    if isinstance(exc, discord.ConnectionClosed) and exc.code == 1000:
                        # clean close, don't re-raise this
                        return
                    raise

                if self.is_closed():
                    return

                # If we get connection reset by peer then try to RESUME
                if isinstance(exc, OSError) and exc.errno in (54, 10054):
                    ws_params.update(sequence=self.ws.sequence, initial=False, resume=True, session=self.ws.session_id)
                    continue

                # We should only get this when an unhandled close code happens,
                # such as a clean disconnect (1000) or a bad state (bad token, no sharding, etc)
                # sometimes, discord sends us 1000 for unknown reasons so we should reconnect
                # regardless and rely on is_closed instead
                if isinstance(exc, discord.ConnectionClosed):
                    if exc.code == 4014:
                        raise discord.PrivilegedIntentsRequired(exc.shard_id) from None
                    if exc.code != 1000:
                        await self.close()
                        raise

                retry = backoff.delay()
                _log.exception("Attempting a reconnect in %.2fs", retry)
                await asyncio.sleep(retry)
                # Always try to RESUME the connection
                # If the connection is not RESUME-able then the gateway will invalidate the session.
                # This is apparently what the official Discord client does.
                ws_params.update(sequence=self.ws.sequence, resume=True, session=self.ws.session_id)

colors_lua = """{[3447003] = "Blue", [15158332] = "Red", [3066993] = "Green", [10181046] = "Purple", [15105570] = "Orange", [15844367] = "Gold", [1752220] = "Teal", [2123412] = "Dark Blue", [10038562] = "Dark Red", [2067276] = "Dark Green", [7419530] = "Dark Purple", [11027200] = "Dark Orange", [12745742] = "Dark Gold", [1146986] = "Dark Teal"}"""
colors = lua.decode(colors_lua)
#print(colors)

#bot = commands.Bot(command_prefix="/", intents=intents)
bot = MyBot(command_prefix="/", intents=discord.Intents.all())
#tree = app_commands.CommandTree(bot)

# == save databases if bot closes/goes offline == #
# async def update_db_on_close():
    #while True:
        #time.sleep(2)
        #if bot.is_closed():
            #countingDB.save()
            #embedDB.save()
            #usersDB.save()
            #print(f"Saved EmbedDB {embedDB.all()}")
            #print(f"Saved CountingDB {countingDB.all()}")
            #print(f"Saved UsersDB {usersDB.all()}")
            #print("Bot Closed, Shutting Down Flask Server.")
            #os._exit(0)

# == update databases every second == #
async def update_db():
    while True:
        await asyncio.sleep(1)
        if not bot.is_closed():
            countingDB.save()
            embedDB.save()
            usersDB.save()
            #print(f"EmbedDB = {embedDB.all()}")
            #print(f"CountingDB = {countingDB.all()}")
            #print(f"UsersDB = {usersDB.all()}")
            for guild in bot.guilds:
                if not countingDB.get(f"{guild.id}"):
                    countingDB.set(f"{guild.id}", {"channel":None,"number":0,"enabled":False,"warnings":0,"lastcounter":None,"highestnumber": 0})
                    countingDB.save()
            #for embed in embedDB.all():
                #print(1)
                #print(f"EmbedDB Key: {embed}, Value: {embedDB.get(embed)}")
            #for info in countingDB.all():
                #print(2)
                #print(f"CountingDB Key: {info}, Value: {countingDB.get(info)}")
            #for users in usersDB.all():
                #print(3)
                #print(f"UsersDB Key: {users}, Value: {usersDB.get(users)}")
            #for user in bot.users:
                #if not usersDB.get(f"{user.id}"):
                    #usersDB.set(f"{user.id}", user.name)
                    #usersDB.save()
# == update databases every second == #

async def update_db():
    while True:
        await asyncio.sleep(1)
        if not bot.is_closed():
            countingDB.save()
            embedDB.save()
            usersDB.save()
            #print(f"EmbedDB = {embedDB.all()}")
            #print(f"CountingDB = {countingDB.all()}")
            #print(f"UsersDB = {usersDB.all()}")
    
            for guild in bot.guilds:
                if not countingDB.get(f"{guild.id}"):
                    countingDB.set(f"{guild.id}", {"channel":None,"number":0,"enabled":False,"warnings":0,"lastcounter":None,"highestnumber":0})
                    countingDB.save()
        if bot.is_closed():
            countingDB.save()
            embedDB.save()
            usersDB.save()
            print(f"Saved EmbedDB {embedDB.all()}")
            print(f"Saved CountingDB {countingDB.all()}")
            print(f"Saved UsersDB {usersDB.all()}")
            print("Bot Closed, Shutting Down Flask Server.")
            os._exit(0)


# === Background task to update cached guilds every 30 seconds ===
async def update_guild_cache():
    global cached_guilds
    while True:
        await bot.tree.sync()
        BotInfo = await bot.application_info()
        cached_guilds = list(bot.guilds)
        print(f"[SYSTEM] Watching {len(cached_guilds)} guilds! Updated List At {time.strftime('%X')}")
        print(f"[SYSTEM] Watching {BotInfo.approximate_user_install_count} Users! As of {time.strftime('%X')}")
        await bot.change_presence(activity=discord.CustomActivity(name=f"🔗 shapes.lol/discord"))
        await asyncio.sleep(2.5)
        #if len(bot.guilds) == 1:
            #print(bot.guilds[0].name)
            #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=bot.guilds[0].name))
        #else:
            #print(f"Watching {len(bot.guilds)} Servers")
            #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers"))

        cached_guilds = []
        await asyncio.sleep(30)

def IsInteger(s):
    try:
        int(s)
        return True  # Conversion succeeded, it is an integer
    except ValueError:
        return False  # Conversion failed, it is not an integer

# === Bot Events ===
@bot.event
async def on_message_delete(message):
    print(f"Message by {message.author} deleted in channel {message.channel}: {message.content}")

    if message.guild: # Check if the message was in a guild
        server = message.guild
        counting = countingDB.get(f"{server.id}")
        if counting:
            if message.author.id == counting['lastcounter'] and message.channel.id == counting['channel'] and IsInteger(message.content) and counting['number'] == message.content:
                nextnumber = counting['number'] + 1
                await message.channel.send(f"{message.author.mention} deleted their message containing the last number. The next number is {nextnumber}")

@bot.event
async def on_message(message):
    # Ignore messages sent by the bot to prevent infinite loops
    if message.author == bot.user:
        return
    if message.author.bot:
        return

    #print(f'Message from {message.author} in #{message.channel}: {message.content}')
    if message.guild:
        messagecontent = message.content
        messagecontent = messagecontent.replace(" ", "")
        if not any(op in messagecontent for op in "+-*/"):
            if IsInteger(messagecontent):
                InputNumber = int(messagecontent)
            else:
                print("stop")
        else:
            num = ''
            parts = []
            for ch in messagecontent:
                if IsInteger(ch):
                    num += ch
                else:
                    parts.append(num)
                    parts.append(ch)
                    num = ''
            parts.append(num)
        
            InputNumber = int(parts[0])
            i = 1
            while i < len(parts):
                op = parts[i]
                val = int(parts[i + 1])
        
                if op == '+':
                    InputNumber += val
                elif op == '-':
                    InputNumber -= val
                elif op == '*':
                    InputNumber *= val
                elif op == '/':
                    result = InputNumber / val
                    InputNumber = int(result) if IsInteger(ch) else result
        
                i += 2
        
        # Print the content of the message
        server = message.guild
        countingjson = countingDB.get(server.id)
        counting_data = countingjson
        number = counting_data['number']
        enabled = counting_data['enabled']
        channel = counting_data['channel']
        warnings = counting_data['warnings']
        LastCounter = counting_data['lastcounter']
        HighestNumber = counting_data['highestnumber']
        next_number = number + 1
        print(next_number)
        if str(InputNumber) == str(next_number) and message.channel.id == channel and enabled == True and message.author.id != LastCounter:
            await message.add_reaction('👍')
            LastCounter = message.author.id
            number = next_number
            #print(number)
            if number > HighestNumber:
                HighestNumber = number
            counting_data['highestnumber'] = HighestNumber
            counting_data['number'] = number
            counting_data["lastcounter"] = LastCounter
            countingDB.set(server.id, counting_data)
            countingDB.save()
        else:
            if enabled == False:
                return
            
            if channel != message.channel.id:
                return
            
            if message.author.id == LastCounter and warnings != 3:
                await message.add_reaction('⚠️')
                await message.reply(f":warning: You can't count by yourself!")
                warnings = warnings + 1
                counting_data['warnings'] = warnings
                countingDB.set(server.id, counting_data)
                countingDB.save()
                return
            if warnings < 3:
                await message.add_reaction('⚠️')
                if number == 0:
                    await message.reply(f":warning: The next number is 1")
                await message.reply(f":warning: The next number is {next_number}")
                warnings = warnings + 1
                counting_data['warnings'] = warnings
                countingDB.set(server.id, counting_data)
                countingDB.save()
                return
            if warnings >= 3:
                message.add_reaction(':x:')
                if number > HighestNumber:
                    HighestNumber = number
                counting_data['highestnumber'] = HighestNumber
                if number == 0:
                    await message.channel.send(f":x: {message.author.mention} ruined it at 1, the next number is 1 (again)")
                    next_number = 1
                    warnings = 0
                    counting_data['warnings'] = warnings
                    counting_data['number'] = number
                    countingDB.set(server.id, counting_data)
                    countingDB.save()
                    return
                await message.channel.send(f":x: {message.author.mention} ruined it at {number}, the next number is 1")
                number = 0
                next_number = 1
                warnings = 0
                LastCounter = None
                counting_data['lastcounter'] = LastCounter
                counting_data['warnings'] = warnings
                counting_data['number'] = number
                countingDB.set(server.id, counting_data)
                countingDB.save()
                return
    else:
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}"
        invite_embed = discord.Embed(
            description=f"[Click Here To Add Shapes To Your Server or Apps]({invite_url})",
            color=embedDB.get(f"{message.author.id}") if embedDB.get(f"{message.author.id}") else discord.Color.blue()
        )
        await message.channel.send(embed=invite_embed)

@bot.event
async def on_ready():
    global bot_ready
    global BotInfo
    bot_ready = True
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")
    BotInfo = await bot.application_info()
    #print(BotInfo)
    await bot.change_presence(activity=discord.CustomActivity(name=f"🔗 shapes.lol/discord"))
    if len(bot.guilds) == 1:
        print(bot.guilds[0].name)
        #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=bot.guilds[0].name))
    else:
        print(f"Watching {len(bot.guilds)} Servers")
        #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers"))
    # Start the cache updater task
    MyBot(command_prefix="/", intents=discord.Intents.all())
    bot.loop.create_task(update_guild_cache())
    bot.loop.create_task(update_db())
    #bot.loop.create_task(update_db_on_close())

@app.route('/server-count', methods=["GET"])
def get_server_count():
    # Ensure the bot is ready before accessing guilds
    if bot.is_ready():
        server_count = len(bot.guilds)
        return str(server_count), 200
    else:
        return "Unknown", 503

@app.route('/user-count', methods=["GET"])
def get_user_count():
    if bot.is_ready():
        user_count = BotInfo.approximate_user_install_count
        return str(user_count), 200
    else:
        return "Unknown", 503

async def restartbot():
    print("Bot Restarting.")
    await bot.close(token)
    await asyncio.sleep(20)
    bot.run(token)


def isotodiscordtimestamp(iso_timestamp_str: str, format_type: str = "f") -> str:
    """
    Converts an ISO 8601 formatted UTC timestamp string to Discord's timestamp markdown.

    Args:
        iso_timestamp_str: The ISO 8601 formatted timestamp string (e.g., "2023-10-27T10:30:00Z").
        format_type: The Discord timestamp format type (e.g., "t", "T", "d", "D", "f", "F", "R").
                    Defaults to "f" (short date/time).

    Returns:
        A string formatted for Discord's timestamp display.
    """
    try:
        # 1. Parse the ISO 8601 string into a datetime object.
        # Use fromisoformat for modern Python versions (3.7+)
        dt_object = datetime.fromisoformat(iso_timestamp_str.replace('Z', '+00:00'))

        # Ensure the datetime object is timezone-aware and in UTC
        if dt_object.tzinfo is None:
            dt_object = pytz.utc.localize(dt_object)
        else:
            dt_object = dt_object.astimezone(pytz.utc)

        # 2. Convert the datetime object to a Unix timestamp.
        unix_timestamp = int(dt_object.timestamp())

        # 3. Format the Unix timestamp into Discord's special timestamp markdown.
        return f"<t:{unix_timestamp}:{format_type}>"
    except ValueError as e:
        return f"Error parsing timestamp: {e}"

# TESTING
#iso_time_utc = "2025-12-25T14:30:00Z"
#discord_time_short = iso_to_discord_time(iso_time_utc, "f")
#discord_time_relative = iso_to_discord_time(iso_time_utc, "R")

#print(f"Short date/time: {discord_time_short}")
#print(f"Long date/time: {discord_time_long}")
#print(f"Relative time: {discord_time_relative}")

DiscordColors = [
    discord.Color.blue(),
    discord.Color.red(),
    discord.Color.green(),
    discord.Color.purple(),
    discord.Color.orange(),
    discord.Color.gold(),
    discord.Color.teal(),
    discord.Color.dark_blue(),
    discord.Color.dark_red(),
    discord.Color.dark_green(),
    discord.Color.dark_purple(),
    discord.Color.dark_orange(),
    discord.Color.dark_gold(),
    discord.Color.dark_teal(),
    discord.Color.random()
]

class EmbedColorSelection(discord.ui.Modal, title="Test Modal"):
    modal_choices = [discord.Color.blue(), discord.Color.red(), discord.Color.green(), discord.Color.purple(), discord.Color.orange(), discord.Color.gold(), discord.Color.teal(), discord.Color.dark_blue(), discord.Color.dark_red(), discord.Color.dark_green(), discord.Color.dark_purple(), discord.Color.dark_orange(), discord.Color.dark_gold(), discord.Color.dark_teal(), discord.Color.random()]
    color_select = discord.ui.Select(
        options=[discord.SelectOption(label="Blue", description="A nice blue color", value=str(discord.Color.blue().value), emoji="🔵"),
        discord.SelectOption(label="Red", description="A vibrant red color", value=str(discord.Color.red().value), emoji="🔴"),
            discord.SelectOption(label="Green", description="A refreshing green color", value=str(discord.Color.green().value), emoji="🟢"),
            discord.SelectOption(label="Purple", description="A royal purple color", value=str(discord.Color.purple().value), emoji="🟣"),
            discord.SelectOption(label="Orange", description="A bright orange color", value=str(discord.Color.orange().value), emoji="🟠"),
            discord.SelectOption(label="Gold", description="A shiny gold color", value=str(discord.Color.gold().value), emoji="🟡"),
            discord.SelectOption(label="Teal", description="A cool teal color", value=str(discord.Color.teal().value), emoji="🔷"),
            discord.SelectOption(label="Dark Blue", description="A deep dark blue color", value=str(discord.Color.dark_blue().value), emoji="🔷"),
            discord.SelectOption(label="Dark Red", description="A deep dark red color", value=str(discord.Color.dark_red().value), emoji="🔴"),
            discord.SelectOption(label="Dark Green", description="A deep dark green color", value=str(discord.Color.dark_green().value), emoji="🟢"),
            discord.SelectOption(label="Dark Purple", description="A deep dark purple color", value=str(discord.Color.dark_purple().value), emoji="🟣"),
            discord.SelectOption(label="Dark Orange", description="A deep dark orange color", value=str(discord.Color.dark_orange().value), emoji="🟠"),
            discord.SelectOption(label="Dark Gold", description="A deep dark gold color", value=str(discord.Color.dark_gold().value), emoji="🟡"),
            discord.SelectOption(label="Dark Teal", description="A deep dark teal color", value=str(discord.Color.dark_teal().value), emoji="🔷"),
            discord.SelectOption(label="Random", description="A random color", value=str(discord.Color.random().value), emoji="🔷"),
        ]
    )
    def __init__(self):
        super().__init__()
        self.add_item(self.color_select)
    async def on_submit(self, interaction: discord.Interaction):
        selected_color_value = int(self.color_select.values[0])
        embedDB.set(f"{interaction.user.id}", selected_color_value)
        embedDB.save()
        embed = discord.Embed(
            title="Embed Color Changed!",
            description=f"Your embed color has been changed successfully to {selected_color_value}!",
            color=selected_color_value
        )
        embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# === User Commands ===
@bot.tree.context_menu(name="sayhitouser")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def sayhitouser(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"Hello, {member.mention}!")

@bot.tree.context_menu(name="discord2spook")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def discord2spook(interaction: discord.Interaction, user: discord.Member): # = <@481295611417853982>):
    url = f"https://api.prp.bio/discord/{user.name}"
    print(url)
    print(user.id)
    response = requests.get(url)
    print(response.text)
    if response.status_code == 200:
        await interaction.response.send_message(f"{user.mention}'s [spook.bio Profile]({response.text})", ephemeral=False)
        print(f"Fetched {response.text} successfully!")
    else:
        if interaction.user.name == user.name:
            await interaction.response.send_message(f":x: You don't have a spook.bio profile linked to your account {user.mention}! :x: To link your profile to your account please DM {owner} or {co_owner}")
            return
        await interaction.response.send_message(f":x: {user.mention} doesn't have a spook.bio profile linked to their account! :x:", ephemeral=False)
        print(f"Error fetching data: {response.status_code}")

# === Message Commands ===
@bot.tree.context_menu(name="google")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def google(interaction: discord.Interaction, message: discord.Message = "shapes.lol"):
    await interaction.response.defer(thinking=True)
    query = message.content
    thinkingembed = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching Google For {query}!",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    await interaction.followup.send(embed=thinkingembed)
    # replace spaces with + in query for google search link
    properquery = query.replace(" ", "+")
    
    url = f"https://www.googleapis.com/customsearch/v1?key={GoogleAPIKey}&cx={searchengine}&q={properquery}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Get First 5 results
        if "items" in data and len(data["items"]) >= 5:
            first_result = data["items"][0]
            title = first_result.get("title", "No Title")
            snippet = first_result.get("snippet", "No Description")
            link = first_result.get("link", "No Link")
            print(f"First Result: {title} - {link}")
            second_result = data["items"][1]
            second_result_title = second_result.get("title", "No Title")
            second_result_snippet = second_result.get("snippet", "No Description")
            second_result_link = second_result.get("link", "No Link")
            print(f"Second Result: {second_result_title} - {second_result_link}")
            third_result = data["items"][2]
            third_result_title = third_result.get("title", "No Title")
            third_result_snippet = third_result.get("snippet", "No Description")
            third_result_link = third_result.get("link", "No Link")
            print(f"Third Result: {third_result_title} - {third_result_link}")
            fourth_result = data["items"][3]
            fourth_result_title = fourth_result.get("title", "No Title")
            fourth_result_snippet = fourth_result.get("snippet", "No Description")
            fourth_result_link = fourth_result.get("link", "No Link")
            print(f"Fourth Result: {fourth_result_title} - {fourth_result_link}")
            fifth_result = data["items"][4]
            fifth_result_title = fifth_result.get("title", "No Title")
            fifth_result_snippet = fifth_result.get("snippet", "No Description")
            fifth_result_link = fifth_result.get("link", "No Link")
            print(f"Fifth Result: {fifth_result_title} - {fifth_result_link}")
            
            embed = discord.Embed(
                title=f"Google Results For {query}",
                description=f"**1. [{title}]({link})**\n{snippet}\n\n**2. [{second_result_title}]({second_result_link})**\n{second_result_snippet}\n\n**3. [{third_result_title}]({third_result_link})**\n{third_result_snippet}\n\n**4. [{fourth_result_title}]({fourth_result_link})**\n{fourth_result_snippet}\n\n**5. [{fifth_result_title}]({fifth_result_link})**\n{fifth_result_snippet}\n\n[Search For More Results](https://google.com/search?q={properquery})",
                color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
            )
            embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=embed)
        else:
            if "items" in data and len(data["items"]) > 0:
                notenoughresultsembed = discord.Embed(
                title=":x: Not enough results found! :x:",
                description=f"Please search on google yourself as there wasn't enough results to generate an embed | [Search on Google Yourself For More Results](https://google.com/search?q={properquery})",
                color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
            )
            noresultembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=notenoughresultsembed)
            noresultembed = discord.Embed(
                title=":x: No results found! :x:",
                description=f"No Results for {query} | [Search on Google Yourself For More Results](https://google.com/search?q={properquery})",
                color=discord.Color.red()
            )
            noresultembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=noresultembed)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        errorembed = discord.Embed(
            title=":x: An error occurred while searching Google. Please try again later. :x:",
            color=discord.Color.red()
        )
        errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
        await interaction.edit_original_response(embed=errorembed)

# === Bot Commands ===
@bot.tree.command(name="userinstalls", description="Get The User Installation Count For Shapes!")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def userinstalls(interaction: discord.Interaction):
    await interaction.response.send_message(f"{BotInfo.approximate_user_install_count} Users Use Shapes!")

@bot.tree.command(name="servercount", description="Get The Server Count For Shapes!")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def userinstalls(interaction: discord.Interaction):
    await interaction.response.send_message(f"{len(bot.guilds)} Servers Use Shapes!")

@bot.tree.command(name="getdata", description="Get The Data From One Of Our Databases")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def getdata(interaction: discord.Interaction, database: str, key: str):
    edata = None
    data = None
    if database == "Counting":
        edata = countingDB.get(f"{key}")
        data = str(edata)
    if database == "Embed":
        edata = embedDB.get(f"{key}")
        data = str(edata)
    if database == "Users":
        edata = usersDB.get(f"{key}")
        data = str(edata)
    if data:
        await interaction.response.send_message(data, ephemeral=True)
    else:
        await interaction.response.send_message(f"No Data Found For {key} In the {database} Database!", ephemeral=True)


@bot.tree.command(name="settings", description="Your Settings For Shapes")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def settings(interaction: discord.Interaction):
    current = embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    # loop through the colors to figure out which one is the current one and set the default value on the selectoption as True
    defaults = []
    for color in DiscordColors:
        if color.value == current:
            defaults.append(True)
        else:
            defaults.append(False)


    view = discord.ui.View()
    color_select = discord.ui.Select(
        placeholder="Select your embed color",
        options=[
            discord.SelectOption(label="Blue", description="A nice blue color", value=str(discord.Color.blue().value), emoji="🔵", default=defaults[0]),
            discord.SelectOption(label="Red", description="A vibrant red color", value=str(discord.Color.red().value), emoji="🔴", default=defaults[1]),
            discord.SelectOption(label="Green", description="A refreshing green color", value=str(discord.Color.green().value), emoji="🟢", default=defaults[2]),
            discord.SelectOption(label="Purple", description="A royal purple color", value=str(discord.Color.purple().value), emoji="🟣", default=defaults[3]),
            discord.SelectOption(label="Orange", description="A bright orange color", value=str(discord.Color.orange().value), emoji="🟠", default=defaults[4]),
            discord.SelectOption(label="Gold", description="A shiny gold color", value=str(discord.Color.gold().value), emoji="🟡", default=defaults[5]),
            discord.SelectOption(label="Teal", description="A cool teal color", value=str(discord.Color.teal().value), emoji="🔷", default=defaults[6]),
            discord.SelectOption(label="Dark Blue", description="A deep dark blue color", value=str(discord.Color.dark_blue().value), emoji="🔷", default=defaults[7]),
            discord.SelectOption(label="Dark Red", description="A deep dark red color", value=str(discord.Color.dark_red().value), emoji="🔴", default=defaults[8]),
            discord.SelectOption(label="Dark Green", description="A deep dark green color", value=str(discord.Color.dark_green().value), emoji="🟢", default=defaults[9]),
            discord.SelectOption(label="Dark Purple", description="A deep dark purple color", value=str(discord.Color.dark_purple().value), emoji="🟣", default=defaults[10]),
            discord.SelectOption(label="Dark Orange", description="A deep dark orange color", value=str(discord.Color.dark_orange().value), emoji="🟠", default=defaults[11]),
            discord.SelectOption(label="Dark Gold", description="A deep dark gold color", value=str(discord.Color.dark_gold().value), emoji="🟡", default=defaults[12]),
            discord.SelectOption(label="Dark Teal", description="A deep dark teal color", value=str(discord.Color.dark_teal().value), emoji="🔷", default=defaults[13]),
            discord.SelectOption(label="Random", description="A random color", value=str(discord.Color.random().value), emoji="🔷", default=defaults[14]),
        ]
    )
    async def on_submit(interaction: discord.Interaction):
        selected_color_value = int(color_select.values[0])
        selected_color_name = colors.get(selected_color_value, "Unknown")
        print(selected_color_name)
        print(color_select)
        print(color_select.values)
        embedDB.set(f"{interaction.user.id}", selected_color_value)
        embed = discord.Embed(
            title="Embed Color Changed!",
            description=f"Your embed color has been changed successfully to {selected_color_name}!",
            color=selected_color_value
        )
        embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    color_select.callback = on_submit
    view.add_item(color_select)

    class SettingsView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)  # No timeout

        @discord.ui.button(label="Change Embed Color", style=discord.ButtonStyle.primary, custom_id="change_embed_color", emoji="🎨")
        async def change_embed_color(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(content="Select an embed color from the menu", view=view, ephemeral=True)
            #await interaction.response.send_modal(EmbedColorModal())
        #@discord.ui.button(label="Toggle Counting", style=discord.ButtonStyle.primary, custom_id="toggle_counting")
        #async def toggle_counting(self, interaction: discord.Interaction, button: discord.ui.Button):
        #    current_setting = countingDB.get("enabled")
        #    if current_setting:
        #        countingDB.set("enabled", False)
        #        await interaction.response.send_message("Counting feature disabled.", ephemeral=True)
        #    else:
        #        countingDB.set("enabled", True)
        #        await interaction.response.send_message("Counting feature enabled.", ephemeral=True)
    embed = discord.Embed(
        title="Settings",
        description="Choose a setting below to modify it.",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
    await interaction.response.send_message(embed=embed, view=SettingsView(), ephemeral=True)


@bot.tree.command(name="status", description=f"Get the {MainURL} status")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"[shapes.lol Status Page](https://spookbio.statuspage.io)")

@bot.tree.command(name="stop", description="Stop the bot.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def stop(interaction: discord.Interaction):
    if interaction.user.name == "lcjunior1220" or interaction.user.name == "sl.ip":
        await interaction.response.send_message(":white_check_mark: Shutdown Successfully!", ephemeral=False)
        await bot.close()
        sys.exit("Bot Stopped.")
    else:
        await interaction.response.send_message(f"Only {owner}, and {co_owner} can use this command.", ephemeral=True)

@bot.tree.command(name="restart", description="Restart the bot.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def restart(interaction: discord.Interaction):
    if interaction.user.name == "lcjunior1220" or interaction.user.name == "sl.ip":
        await interaction.response.send_message(":white_check_mark: Restarted Successfully!!", ephemeral=False)
        await restartbot()
    else:
        await interaction.response.send_message(f"Only {owner}, and {co_owner} can use this command.", ephemeral=True)

@bot.tree.command(name="counting", description="Counting Settings")
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(add_reactions=True, moderate_members=True, read_message_history=True, view_channel=True, send_messages=True)
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def counting(interaction: discord.Interaction):
    server = interaction.guild
    print(server.id)
    counting_json = countingDB.get(server.id)
    countingData = counting_json
    print(countingData)
    if not countingData:
        countingDB.set(server.id, {"channel":None,"number":0,"enabled":False,"warnings":0,"lastcounter":None})
        countingDB.save()
        counting_json = countingDB.get(server.id)
        countingData = counting_json
    print(countingData)
    print(countingData['channel'])
    print(countingData['number'])
    print(countingData['enabled'])
    print(countingData['warnings'])
    print(countingData['lastcounter'])
    channels = server.channels
    channel_options = []
    ccount = 0
    for channel in channels:
        ccount = ccount + 1
        if isinstance(channel, discord.TextChannel) and ccount != 25:
            channel_options.append(discord.SelectOption(label=channel.name, value=str(channel.id)))
    class CountingView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)  # No timeout

        @discord.ui.button(label="Toggle Counting", style=discord.ButtonStyle.primary, custom_id="toggle_counting", emoji="🔢")
        async def toggle_counting(self, interaction: discord.Interaction, button: discord.ui.Button):
            counting_json = countingDB.get(server.id)
            countingData = counting_json
            current_setting = countingData['enabled']
            if current_setting:
                countingData['enabled'] = False
                countingDB.set(server.id, countingData)
                await interaction.response.send_message("Counting disabled.", ephemeral=True)
            else:
                countingData['enabled'] = True
                countingDB.set(server.id, countingData)
                await interaction.response.send_message("Counting enabled.", ephemeral=True)

        @discord.ui.select(placeholder="Select Counting Channel", options=channel_options, custom_id="select_channel")
        async def select_channel(self, interaction: discord.Interaction, select: discord.ui.Select):
            selected_channel_id = int(select.values[0])
            counting_json = countingDB.get(server.id)
            countingData = counting_json
            countingData['channel'] = selected_channel_id
            countingDB.set(server.id, countingData)
            await interaction.response.send_message(f"Counting channel set to <#{selected_channel_id}>.", ephemeral=True)
    embed = discord.Embed(
        title="Counting Settings",
        description=f"**Current Settings:**\n- Counting Enabled: `{countingData['enabled']}`\n- Counting Channel: `<#{countingData['channel']}>`\n- Current Number: `{countingData['number']}`\n- Highest Number: `{countingData['highestnumber']}`\n- Warnings: `{countingData['warnings']}`\n- Last Counter: `{countingData['lastcounter']}`",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
    await interaction.response.send_message(embed=embed, view=CountingView(), ephemeral=True)


@bot.tree.command(name="spookpfp", description="Get a pfp from a user's spook.bio profile.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def spookpfp(interaction: discord.Interaction, username: str = "phis"):
    url = f"https://spook.bio/u/{username}/pfp.jpg"
    response = requests.get(url)
    if response.status_code == 200:
        await interaction.response.send_message(url, ephemeral=False)
        print("Fetched data successfully!")
    else:
        await interaction.response.send_message(f":x: {response.status_code} Not Found :x:", ephemeral=True)
        print(f"Error fetching data: {response.status_code}")

@bot.tree.command(name="discord2spook", description="Get a spook.bio profile from a discord user.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def discord2spook(interaction: discord.Interaction, user: discord.Member): # = <@481295611417853982>):
    url = f"https://api.prp.bio/discord/{user.name}"
    print(user.id)
    print(url)
    response = requests.get(url)
    print(response.text)
    if response.status_code == 200:
        await interaction.response.send_message(f"{user.mention}'s [spook.bio Profile]({response.text})", ephemeral=False)
        print(f"Fetched {response.text} successfully!")
    else:
        if interaction.user.name == user.name:
            await interaction.response.send_message(f":x: You don't have a spook.bio profile linked to your account {user.mention}! :x: To link your profile to your account please DM {owner} or {co_owner}")
            return
        await interaction.response.send_message(f":x: {user.mention} doesn't have a spook.bio profile linked to their account! :x:", ephemeral=False)
        print(f"Error fetching data: {response.status_code}")

@bot.tree.command(name="ping", description="Check the bot's latency.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ping(interaction: discord.Interaction):
    latency = bot.latency * 1000
    connection = "Good" if latency < 200 else "Average" if latency < 400 else "Poor"
    embed = discord.Embed(
        title="Bot Server Stats"
        , description=f"Latency: `{latency:.2f}ms` ({connection} Connection)"
        , color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(10)
    updatedlatency = bot.latency * 1000
    updatedconnection = "Good" if updatedlatency < 200 else "Average" if updatedlatency < 400 else "Poor"
    embed = discord.Embed(
        title="Bot Server Stats"
        , description=f"OriginalLatency: `{latency:.2f}ms` ({connection} Connection)\nEditLatency: `{updatedlatency:.2f}ms` ({updatedconnection} Connection)"
        , color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
    await interaction.edit_original_response(embed=embed, content=None)

@bot.tree.command(name="roblox2discord", description="Get a roblox user's Discord from their username.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def roblox2discord(interaction: discord.Interaction, user: str = "Roblox"):

    print(f"Searching For {user}")
    await interaction.response.defer(thinking=True)
    thinkingembed = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching For {user}!",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    await interaction.followup.send(embed=thinkingembed)

    url = "https://users.roblox.com/v1/usernames/users"
    # print(f"Fetching Data From {url}")
    
    request_payload = {
        "usernames": [user],
        "excludeBannedUsers": True
    }

    try:
        response = requests.post(url, json=request_payload)
        response.raise_for_status()
        data = response.json()
        if data.get("data") and len(data["data"]) > 0:
            userinfo = data["data"][0]
            UserID = userinfo["id"]
            Display = userinfo["displayName"]
            user = userinfo["name"]
            print(f"UserInfo: {userinfo}")

        else:
            print(f"{user} not found.")
            failedembed7 = discord.Embed(
                title=f":warning: {user} not found.",
                color=discord.Color.yellow()
            )
            await interaction.edit_original_response(embed=failedembed7)
            return

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        failedembed8 = discord.Embed(
            title=f":warning: {user} not found.",
            color=discord.Color.yellow()
        )
        await interaction.edit_original_response(embed=failedembed8)
        return

    url = f"https://api.ropro.io/getUserInfoTest.php?userid={UserID}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        RoProData = response.json()
        print(RoProData)
        Discord = RoProData["discord"]    
        if Discord != "":
            embed = discord.Embed(
                title=f"{user}'s Discord Username",
                description=f"```{Discord}```",
                color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
            )
            embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=embed)
            #await interaction.edit_original_response(f"{user}'s Discord (RoPro): ```{Discord}```")
            return
        else:
            embed = discord.Embed(
                title=f":x: {user} does not have Discord linked to their profile! :x:",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=embed)
            #await interaction.edit_original_response(f"{user} does not have Discord linked to their profile!")
            return    
    except requests.exceptions.RequestException as e:
                print(f"Error fetching RoPro data for ID {UserID}: {e}")
                failedembed2 = discord.Embed(
                    title=f"Error retrieving Discord User from {user}",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=failedembed2)
                # await interaction.edit_original_response(f"Error retrieving Discord User from {url}")
                return

@bot.tree.command(name="google", description="Search Something On Google.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def google(interaction: discord.Interaction, query: str = "shapes.lol"):
    await interaction.response.defer(thinking=True)
    thinkingembed = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching Google For {query}!",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    await interaction.followup.send(embed=thinkingembed)
    
    # replace spaces with + in query for google search link
    properquery = query.replace(" ", "+")
    
    url = f"https://www.googleapis.com/customsearch/v1?key={GoogleAPIKey}&cx={searchengine}&q={properquery}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Get First 5 results
        if "items" in data and len(data["items"]) > 0:
            first_result = data["items"][0]
            title = first_result.get("title", "No Title")
            snippet = first_result.get("snippet", "No Description")
            link = first_result.get("link", "No Link")
            print(f"First Result: {title} - {link}")
            second_result = data["items"][1]
            second_result_title = second_result.get("title", "No Title")
            second_result_snippet = second_result.get("snippet", "No Description")
            second_result_link = second_result.get("link", "No Link")
            print(f"Second Result: {second_result_title} - {second_result_link}")
            third_result = data["items"][2]
            third_result_title = third_result.get("title", "No Title")
            third_result_snippet = third_result.get("snippet", "No Description")
            third_result_link = third_result.get("link", "No Link")
            print(f"Third Result: {third_result_title} - {third_result_link}")
            fourth_result = data["items"][3]
            fourth_result_title = fourth_result.get("title", "No Title")
            fourth_result_snippet = fourth_result.get("snippet", "No Description")
            fourth_result_link = fourth_result.get("link", "No Link")
            print(f"Fourth Result: {fourth_result_title} - {fourth_result_link}")
            fifth_result = data["items"][4]
            fifth_result_title = fifth_result.get("title", "No Title")
            fifth_result_snippet = fifth_result.get("snippet", "No Description")
            fifth_result_link = fifth_result.get("link", "No Link")
            print(f"Fifth Result: {fifth_result_title} - {fifth_result_link}")
            
            embed = discord.Embed(
                title=f"Google Results For {query}",
                description=f"**1. [{title}]({link})**\n{snippet}\n\n**2. [{second_result_title}]({second_result_link})**\n{second_result_snippet}\n\n**3. [{third_result_title}]({third_result_link})**\n{third_result_snippet}\n\n**4. [{fourth_result_title}]({fourth_result_link})**\n{fourth_result_snippet}\n\n**5. [{fifth_result_title}]({fifth_result_link})**\n{fifth_result_snippet}\n\n[Search For More Results](https://google.com/search?q={properquery})",
                color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
            )
            embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=embed)
        else:
            noresultembed = discord.Embed(
                title=":x: No results found! :x:",
                description=f"No Results for {query} | [Search on Google Yourself For More Results](https://google.com/search?q={properquery})",
                color=discord.Color.red()
            )
            noresultembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=noresultembed)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        errorembed = discord.Embed(
            title=":x: An error occurred while searching Google. Please try again later. :x:",
            color=discord.Color.red()
        )
        errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
        await interaction.edit_original_response(embed=errorembed)

@bot.tree.command(name="invite", description="Get the bot's invite link.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def invite(interaction: discord.Interaction):
    invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}"
    invite_embed = discord.Embed(
        description=f"[Click Here To Add Shapes To Your Server or Apps]({invite_url})",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    invite_embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
    await interaction.response.send_message(embed=invite_embed, ephemeral=False)
    #await interaction.response.send_message(f"Invite me to your server or add me to your apps using this link: {invite_url}", ephemeral=False)

@bot.tree.command(name="robloxinfo", description="Get a Roblox user's profile information.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def robloxinfo(interaction: discord.Interaction, user: str = "Roblox"):
    
    print(f"Searching For {user}'s profile")
    await interaction.response.defer(thinking=True)
    thinkingembed = discord.Embed(
                title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching For {user}'s Roblox Profile!",
                color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
            )
    await interaction.followup.send(embed=thinkingembed)

    url = "https://users.roblox.com/v1/usernames/users"
    
    request_payload = {
        "usernames": [user],
        "excludeBannedUsers": False
    }

    try:
        response = requests.post(url, json=request_payload)
        response.raise_for_status()
        data = response.json()
        if data.get("data") and len(data["data"]) > 0:
            userinfo = data["data"][0]
            UserID = userinfo["id"]
            Display = userinfo["displayName"]
            hasVerifiedBadge = userinfo.get("hasVerifiedBadge", False)
            print(f"UserInfo: {userinfo}")

            rolimons_headers = {
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'referer': 'https://www.rolimons.com/',
                'origin': 'https://www.rolimons.com/',
                'user-agent': 'shapes.lol'
            }
            
            rolimons_payload = {
                "player_name": user
            }
            
            try:
                rolimons_response = requests.post(
                    "https://api.rolimons.com/players/v1/addplayerbyname",
                    headers=rolimons_headers,
                    json=rolimons_payload
                )
                rolimons_response.raise_for_status()
                rolimons_data = rolimons_response.json()
                print(f"Rolimons API Response: {rolimons_data}")
                
                if rolimons_data.get("success") == True:
                    print(f"Successfully added {user} to Rolimons with ID: {rolimons_data.get('player_id')}")
                elif rolimons_data.get("code") == 12:
                    print(f"Player {user} already exists on Rolimons")
                else:
                    print(f"Rolimons API returned: {rolimons_data}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Error calling Rolimons API: {e}")

            url = f"https://users.roblox.com/v1/users/{UserID}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                playerdata = response.json()
                print(playerdata)
                Description = playerdata["description"]
                Banned = playerdata["isBanned"]
                user = playerdata["name"]
                JoinDate = playerdata["created"]
                RobloxJoinDate_DiscordTimestamp = isotodiscordtimestamp(JoinDate, "F")
            except requests.exceptions.RequestException as e:
                print(f"Error fetching user data for ID {UserID}: {e}")
                failedembed = discord.Embed(
                    title=f":x: An error occurred while fetching data for user ID: {UserID}. Please try again later.",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=failedembed)
                return

            if Display == user:
                Username = Display
            else:
                Username = f"{Display} (@{user})"
            
            if hasVerifiedBadge:
                Username += " <:RobloxVerified:1416951927513677874>"

            if Banned:
                Username = f":warning: [Account Deleted] {Username}"

            url = f"https://api.ropro.io/getUserInfoTest.php?userid={UserID}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                RoProData = response.json()
                print(RoProData)
                Discord = RoProData["discord"]
            
            except requests.exceptions.RequestException as e:
                print(f"Error fetching RoPro data for ID {UserID}: {e}")
                failedembed2 = discord.Embed(
                    title=f"Error retrieving Discord User from {url}",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=failedembed2)
                return

            profileurl = f"https://www.roblox.com/users/{UserID}/profile"
            rolimonsurl = f"https://rolimons.com/player/{UserID}"

            view = discord.ui.View()
            if not Banned:
                view.add_item(discord.ui.Button(
                    label="View Profile",
                    style=discord.ButtonStyle.link,
                    emoji="<:RobloxLogo:1416951004607418398>",
                    url=profileurl
            ))
            view.add_item(discord.ui.Button(
                label="View Profile On Rolimons",
                style=discord.ButtonStyle.link,
                emoji="<:RolimonsLogo:1417258794974711901>",
                url=rolimonsurl
            ))

            embed = discord.Embed(
                title=Username,
                url=profileurl,
                description=Description,
                color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
            )
            if Discord != "":
                embed.add_field(
                    name="Discord (RoPro)",
                    value=f"```\n{Discord}\n```",
                    inline=False
                )
            
            embed.add_field(name="Username", value=user, inline=False)
            embed.add_field(name="UserID", value=UserID, inline=False)
            embed.add_field(name="Join Date", value=RobloxJoinDate_DiscordTimestamp, inline=False)

            url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={UserID}&size=420x420&format=Png&is=false"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                if data and data.get("data") and len(data["data"]) > 0:
                    HeadShot = data["data"][0].get("imageUrl")
                    embed.set_author(name=user, url=profileurl, icon_url=HeadShot)
                    print(data)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching avatar headshot: {e}")
                failedembed4 = discord.Embed(
                    title=f"Failed To Retrieve {user}'s Headshot!",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=failedembed4)
                return

            url = f"https://thumbnails.roblox.com/v1/users/avatar-bust?userIds={UserID}&size=150x150&format=Png&isCircular=false"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                if data and data.get("data") and len(data["data"]) > 0:
                    AvatarBust = data["data"][0].get("imageUrl")
                    embed.set_thumbnail(url=AvatarBust)
                    embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
                    print(data)
                    await interaction.edit_original_response(embed=embed, view=view)
                    return
                else:
                    print(f"Error fetching avatar bust: {e}")
                    failedembed5 = discord.Embed(
                        title=f"Failed To Retrieve {user}'s avatar bust!",
                        color=discord.Color.red()
                )
                    await interaction.edit_original_response(embed=failedembed5)
                    return
            except requests.exceptions.RequestException as e:
                print(f"Error fetching avatar bust: {e}")
                failedembed6 = discord.Embed(
                    title=f"Failed To Retrieve {user}'s avatar bust!",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=failedembed6)
                return
        else:
            print(f"{user} not found.")
            failedembed7 = discord.Embed(
                title=f":warning: {user} not found.",
                color=discord.Color.yellow()
            )
            await interaction.edit_original_response(embed=failedembed7)
            return
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        failedembed8 = discord.Embed(
            title=f":warning: {user} not found.",
            color=discord.Color.yellow()
        )
        await interaction.edit_original_response(embed=failedembed8)
        return

@bot.tree.command(name="britishuser", description="Check if a user has their language set to British English")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def british_check(interaction: discord.Interaction, user_input: str):
    await interaction.response.defer(thinking=True)
    
    embed_color = embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    
    thinkingembed = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Checking if {user_input} is British!",
        color=embed_color
    )
    await interaction.followup.send(embed=thinkingembed)

    url = "https://users.roblox.com/v1/usernames/users"
    
    request_payload = {
        "usernames": [user_input],
        "excludeBannedUsers": False
    }

    try:
        response = requests.post(url, json=request_payload)
        response.raise_for_status()
        data = response.json()
        if data.get("data") and len(data["data"]) > 0:
            userinfo = data["data"][0]
            UserID = userinfo["id"]
            username = userinfo["name"]

            payload = json.dumps([{"name": "vieweeUserId", "type": "UserId", "value": int(UserID)}])
            b64encoded = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
            
            british_url = f"https://apis.roblox.com/access-management/v1/upsell-feature-access?featureName=MustHideConnections&extraParameters={b64encoded}"
            british_response = requests.get(british_url)
            british_response.raise_for_status()
            british_data = british_response.json()
            
            is_british = british_data.get("access") == "Granted"

            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-bust?userIds={UserID}&size=150x150&format=Png&isCircular=false"
            avatar_response = requests.get(avatar_url)
            avatar_data = avatar_response.json()
            avatar_thumbnail = avatar_data["data"][0]["imageUrl"] if avatar_data.get("data") and len(avatar_data["data"]) > 0 else None

            if is_british:
                embed = discord.Embed(
                    title=":flag_gb: British Check Result",
                    description=f"**{username}** is British! :flag_gb:",
                    color=embed_color
                )
            else:
                embed = discord.Embed(
                    title=":x: British Check Result",
                    description=f"**{username}** is not British :x:",
                    color=embed_color
                )
            
            if avatar_thumbnail:
                embed.set_thumbnail(url=avatar_thumbnail)
            
            embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=embed)
            
        else:
            embed = discord.Embed(
                title=f":warning: {user_input} not found",
                color=embed_color
            )
            embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=embed)
            
    except requests.exceptions.RequestException as e:
        embed = discord.Embed(
            title=":x: API Error",
            description=f"An error occurred: {str(e)}",
            color=embed_color
        )
        embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
        await interaction.edit_original_response(embed=embed)

@bot.tree.command(name="iteminfo", description="Get detailed information about a Roblox item")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def item(interaction: discord.Interaction, item_query: str = "Dominus Empyreus"):
    
    print(f"Searching For {item_query}'s item info")
    await interaction.response.defer(thinking=True)
    thinkingembed = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching For {item_query}'s Item Information!",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    await interaction.followup.send(embed=thinkingembed)

    if not item_query.isdigit():
        search_url = f"https://catalog.roblox.com/v1/search/items?category=All&limit=10&keyword={urllib.parse.quote(item_query)}"
        
        try:
            response = requests.get(search_url)
            response.raise_for_status()
            search_data = response.json()
            
            if search_data.get("data") and len(search_data["data"]) > 0:
                item_id = None
                for item in search_data["data"]:
                    if item.get("name", "").lower() == item_query.lower():
                        item_id = item.get("id")
                        break
                
                if not item_id:
                    item_id = search_data["data"][0].get("id")
                
                if not item_id:
                    failedembed = discord.Embed(
                        title=f":warning: {item_query} not found.",
                        color=discord.Color.yellow()
                    )
                    await interaction.edit_original_response(embed=failedembed)
                    return
            else:
                failedembed = discord.Embed(
                    title=f":warning: {item_query} not found.",
                    color=discord.Color.yellow()
                )
                await interaction.edit_original_response(embed=failedembed)
                return
                
        except requests.exceptions.RequestException as e:
            print(f"Error searching for item {item_query}: {e}")
            failedembed = discord.Embed(
                title=f":x: An error occurred while searching for {item_query}. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=failedembed)
            return
    else:
        item_id = item_query

    url = f"https://catalog.roblox.com/v1/catalog/items/{item_id}/details?itemType=Asset"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        item_data = response.json()
        print(f"ItemData: {item_data}")

        name = item_data.get("name", "Unknown Item")
        description = item_data.get("description", "No description available")
        creator_name = item_data.get("creatorName", "Unknown Creator")
        creator_type = item_data.get("creatorType", "User")
        creator_verified = item_data.get("creatorHasVerifiedBadge", False)
        lowest_price = item_data.get("lowestPrice", 0)
        is_purchasable = item_data.get("isPurchasable", False)
        item_type = item_data.get("itemType", "Asset")
        
        details_url = f"https://economy.roblox.com/v2/assets/{item_id}/details"
        try:
            details_response = requests.get(details_url)
            details_response.raise_for_status()
            details_data = details_response.json()
            
            created_date = details_data.get("Created")
            updated_date = details_data.get("Updated")
            
            if created_date:
                created_timestamp = isotodiscordtimestamp(created_date, "F")
            else:
                created_timestamp = "Unknown"
                
            if updated_date:
                updated_timestamp = isotodiscordtimestamp(updated_date, "F")
            else:
                updated_timestamp = "Unknown"
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching item details: {e}")
            created_timestamp = "Unknown"
            updated_timestamp = "Unknown"

        creator_display = creator_name
        if creator_verified:
            creator_display += " <:RobloxVerified:1416951927513677874>"
        else:
            creator_display += f" ({creator_type})"

        price_display = "Not for sale"
        if is_purchasable and lowest_price is not None:
            price_display = "Free" if lowest_price == 0 else f"{lowest_price:,} Robux"

        thumbnail_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={item_id}&size=420x420&format=Png"
        try:
            thumb_response = requests.get(thumbnail_url)
            thumb_response.raise_for_status()
            thumb_data = thumb_response.json()
            if thumb_data and thumb_data.get("data") and len(thumb_data["data"]) > 0:
                image_url = thumb_data["data"][0].get("imageUrl")
            else:
                image_url = None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching item thumbnail: {e}")
            image_url = None

        embed = discord.Embed(
            title=name,
            url=f"https://www.roblox.com/catalog/{item_id}/",
            description=description,
            color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
        )

        if image_url:
            embed.set_thumbnail(url=image_url)

        embed.add_field(name="Item ID", value=item_id, inline=True)
        embed.add_field(name="Item Type", value=item_type, inline=True)
        embed.add_field(name="Price", value=price_display, inline=True)
        embed.add_field(name="Creator", value=creator_display, inline=True)
        embed.add_field(name="Created", value=created_timestamp, inline=True)
        embed.add_field(name="Updated", value=updated_timestamp, inline=True)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="View Item",
            style=discord.ButtonStyle.link,
            emoji="<:RobloxLogo:1416951004607418398>",
            url=f"https://www.roblox.com/catalog/{item_id}/"
        ))

        embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
        await interaction.edit_original_response(embed=embed, view=view)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching item data for ID {item_id}: {e}")
        failedembed = discord.Embed(
            title=f":x: An error occurred while fetching data for item ID: {item_id}. Please try again later.",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=failedembed)
        return

@bot.tree.command(name="groupinfo", description="Get information about a Roblox group")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def groupinfo(interaction: discord.Interaction, group_id: str):
    
    print(f"Searching For group ID {group_id}")
    await interaction.response.defer(thinking=True)
    thinkingembed = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching For Group ID {group_id}!",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    await interaction.followup.send(embed=thinkingembed)

    url = f"https://groups.roblox.com/v1/groups/{group_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        group_data = response.json()
        print(f"GroupData: {group_data}")

        name = group_data.get("name", "Unknown Group")
        description = group_data.get("description", "No description available")
        member_count = group_data.get("memberCount", 0)
        group_verified = group_data.get("hasVerifiedBadge", False)
        public_entry = group_data.get("publicEntryAllowed", False)
        owner_data = group_data.get("owner", {})
        owner_id = owner_data.get("userId")
        owner_name = owner_data.get("username", "Unknown")

        # Force verified badges for specific group and user
        if group_id == "5544706":
            group_verified = True
        
        if str(owner_id) == "124767284":
            owner_verified = True
        else:
            owner_verified = owner_data.get("hasVerifiedBadge", False)

        group_display = name
        if group_verified:
            group_display += " <:RobloxVerified:1416951927513677874>"

        owner_display = owner_name
        if owner_verified:
            owner_display += " <:RobloxVerified:1416951927513677874>"

        entry_status = "Public" if public_entry else "Private"

        thumbnail_url = f"https://thumbnails.roblox.com/v1/groups/icons?groupIds={group_id}&size=150x150&format=Png&isCircular=false"
        try:
            thumb_response = requests.get(thumbnail_url)
            thumb_response.raise_for_status()
            thumb_data = thumb_response.json()
            if thumb_data and thumb_data.get("data") and len(thumb_data["data"]) > 0:
                image_url = thumb_data["data"][0].get("imageUrl")
            else:
                image_url = None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching group thumbnail: {e}")
            image_url = None

        embed = discord.Embed(
            title=group_display,
            url=f"https://www.roblox.com/communities/{group_id}",
            description=description,
            color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
        )

        if image_url:
            embed.set_thumbnail(url=image_url)

        embed.add_field(name="Group ID", value=group_id, inline=True)
        embed.add_field(name="Members", value=f"{member_count:,}", inline=True)
        embed.add_field(name="Entry", value=entry_status, inline=True)
        embed.add_field(name="Owner", value=owner_display, inline=True)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="View Group",
            style=discord.ButtonStyle.link,
            emoji="<:RobloxLogo:1416951004607418398>",
            url=f"https://www.roblox.com/communities/{group_id}"
        ))

        embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
        await interaction.edit_original_response(embed=embed, view=view)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching group data for ID {group_id}: {e}")
        failedembed = discord.Embed(
            title=f":x: An error occurred while fetching data for group ID: {group_id}. Please try again later.",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=failedembed)
        return

# === Flask Runner in Thread ===
def run_flask():
    port = int(os.environ.get("PORT", 13455))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)

# === Run Bot + Flask Webserver ===
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(token)
