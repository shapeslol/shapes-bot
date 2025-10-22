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
import re
import socket
import typing
from typing import Dict, Any, Optional
from openai import OpenAI

# Setup Emojis
Emojis = [
        ["Loading"] = "<a:loading:1416950730094542881>"
            ["Roblox"] = [
                    ["rolimons"] = "<:RolimonsLogo:1417258794974711901>",
                            ["logo"] = "<:RobloxLogo:1416951004607418398>"
                                    ["verified"] ="<:RobloxVerified:1416951927513677874>",
                                            ["premium"] = "<:RobloxPremium:1416951078200541378>",
                                                    ["admin"] = "<:RobloxAdmin:1416951128876122152>",
                                                            ["inviter"] = "<:RobloxInviter:1416952415772479559>",
                                                                    ["modelmaker"] ="<:RobloxModelMaker:1416952360852mith"] = "<:Roblox1000Visits:1416952101229170698>",
                                                                                            ["homestead"] = "<:Roblox100Visits:1416952056324952184>",
                                                                                                    ["ambassador"] = "<:Ambassador:1430627877337960548>",
                                                                                                            ["friendship"] = "<:Friendship:1430641140679577630>",
                                                                                                                    ["warrior"] = "<:Warrior:1430640757403943063>",           
                                                                                                                            ["game"] = "<:RobloxInGame:14306403353939150
]


# OpenAI client
chatgpt = OpenAI(api_key=os.getenv("OpenAI_KEY"))

#=== Database Setup ===
countingDB = PickleDB('counting.db')
embedDB = PickleDB('embed.db')
usersDB = PickleDB('users.db')
autoroleDB = PickleDB('autorole.db')
AI_DB = PickleDB('ai.db')

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

# == update databases 0.5 seconds == #

async def update_db():
    while True:
        await asyncio.sleep(0.5)
        if not bot.is_closed():
            countingDB.save()
            embedDB.save()
            usersDB.save()
            autoroleDB.save()
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
            autoroleDB.save()
            AI_DB.save()
            print(f"Saved EmbedDB {embedDB.all()}")
            print(f"Saved CountingDB {countingDB.all()}")
            print(f"Saved UsersDB {usersDB.all()}")
            print(f"Saved AutoRoleDB {autoroleDB.all()}")
            print(f"Saved AI_DB {AI_DB.all()}")
            print("Bot Closed, Shutting Down Flask Server.")
            os._exit(0)


# === Background task to update cached guilds every 2 seconds ===
async def update_guild_cache():
    global cached_guilds
    while True:
        #await bot.tree.sync()
        BotInfo = await bot.application_info()
        cached_guilds = list(bot.guilds)
        print(f"[SYSTEM] Watching {len(cached_guilds)} Servers!")
        print(f"[SYSTEM] Watching {BotInfo.approximate_user_install_count} Users!")
        await bot.change_presence(activity=discord.CustomActivity(name=f"🔗 shapes.lol/discord"))
        await asyncio.sleep(2)
        #if len(bot.guilds) == 1:
            #print(bot.guilds[0].name)
            #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=bot.guilds[0].name))
        #else:
            #print(f"Watching {len(bot.guilds)} Servers")
            #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers"))

        await asyncio.sleep(30)

def IsInteger(s):
    try:
        int(s)
        return True  # Conversion succeeded, it is an integer
    except ValueError:
        return False  # Conversion failed, it is not an integer

# === Bot Events ===
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.author.bot:
        return

    if message.guild:
        server = message.guild
        countingjson = countingDB.get(server.id)
        counting_data = countingjson
        enabled = counting_data['enabled']
        number = counting_data['number']
        channel = counting_data['channel']
        warnings = counting_data['warnings']
        LastCounter = counting_data['lastcounter']
        HighestNumber = counting_data['highestnumber']
        next_number = number + 1
        if enabled == False or message.channel.id != channel:
            return
        
        messagecontent = message.content
        messagecontent = messagecontent.replace(" ", "")
        InputNumber = None
        
        if not any(op in messagecontent for op in "+-*/x"):
            if IsInteger(messagecontent):
                InputNumber = int(messagecontent)
            else:
                ##print("stop")
                return
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
        
            if not IsInteger(parts[0]):
                return
            InputNumber = int(parts[0])
            i = 1
            while i < len(parts):
                op = parts[i]
                val = int(parts[i + 1])
        
                if op == '+':
                    InputNumber += val
                elif op == '-':
                    InputNumber -= val
                elif op == '*' or op == 'x':
                    InputNumber *= val
                elif op == '/':
                    result = InputNumber / val
                    InputNumber = int(result) if IsInteger(ch) else result
        
                i += 2
        
        if str(InputNumber) == str(next_number) and message.author.id != LastCounter:
            await message.add_reaction('👍')
            LastCounter = message.author.id
            number = next_number
            if number > HighestNumber:
                HighestNumber = number
            counting_data['highestnumber'] = HighestNumber
            counting_data['number'] = number
            counting_data["lastcounter"] = LastCounter
            countingDB.set(server.id, counting_data)
            countingDB.save()
        else:
            if InputNumber == None:
                return
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
                await message.add_reaction('❌')
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
async def on_message_delete(message):
    print(f"Message by {message.author} deleted in channel {message.channel}: {message.content}")

    if message.guild:
        server = message.guild
        counting = countingDB.get(f"{server.id}")
        if counting:
            if message.author.id == counting['lastcounter'] and message.channel.id == counting['channel'] and IsInteger(message.content):
                nextnumber = counting['number'] + 1
                await message.channel.send(f"{message.author.mention} deleted their message containing the last number. The next number is {nextnumber}")

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return

    if before.guild:
        server = before.guild
        counting = countingDB.get(f"{server.id}")
        if counting:
            if before.author.id == counting['lastcounter'] and before.channel.id == counting['channel'] and IsInteger(before.content):
                nextnumber = counting['number'] + 1
                await before.channel.send(f"{before.author.mention} edited their message containing the last number. The next number is {nextnumber}")

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

@bot.event
async def on_member_join(member):
    if member.bot:
        return
        
    autorole_data = autoroleDB.get(f"{member.guild.id}")
    if autorole_data and autorole_data.get("enabled"):
        role_id = autorole_data.get("role_id")
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)

@app.route('/botinfo', methods=["GET"])
def get_bot_info():
    # Ensure the bot is ready before accessing guilds
    if bot.is_ready():
        server_count = len(bot.guilds)
        jsonData = {"Servers":str(server_count),"Users":str(BotInfo.approximate_user_install_count)}
        return jsonify(jsonData), 200
    else:
        jsonData = {"Servers":"Unknown","Users":"Unknown"}
        return jsonify(jsonData), 503

@app.route('/clb', methods=["GET"])
def countinglb():
    if bot.is_ready():
        lb = {}
        for server in countingDB.all():
            data = countingDB.get(f"{server}")
            lb[f"{server}"] = {"currentnumber": data['number'],"highestnumber": data['highestnumber'], "serverName": bot.get_guild(int(server)).name if bot.get_guild(int(server)) else "Unknown"}
        FullLB = sorted(lb.items(), key=lambda x: x[1]['highestnumber'], reverse=True)
        return {"Leaderboard":FullLB}, 200
    else:
        return {"Unknown"}, 503

async def restartbot():
    print("Bot Restarting.")
    await bot.close(token)
    await asyncio.sleep(20)
    bot.run(token)

def isotodiscordtimestamp(iso_timestamp_str: str, format_type: str = "f") -> str:
    try:
        if '.' in iso_timestamp_str and iso_timestamp_str.endswith('Z'):
            main_part = iso_timestamp_str.split('.')[0]
            iso_timestamp_str = main_part + '+00:00'
        elif '.' in iso_timestamp_str and '+00:00' in iso_timestamp_str:
            main_part = iso_timestamp_str.split('.')[0]
            iso_timestamp_str = main_part + '+00:00'
        elif iso_timestamp_str.endswith('Z'):
            iso_timestamp_str = iso_timestamp_str.replace('Z', '+00:00')
        
        dt_object = datetime.fromisoformat(iso_timestamp_str)

        if dt_object.tzinfo is None:
            dt_object = pytz.utc.localize(dt_object)
        else:
            dt_object = dt_object.astimezone(pytz.utc)

        unix_timestamp = int(dt_object.timestamp())
        return f"<t:{unix_timestamp}:{format_type}>"
    except ValueError as e:
        return None

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
        title=f"{Emojis["Loading"] interaction.user.mention} Searching Google For {query}!",
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
@app_commands.default_permissions(administrator=True)
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
        countingDB.set(server.id, {"channel":None,"number":0,"enabled":False,"warnings":0,"lastcounter":None,"highestnumber":0})
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
            super().__init__(timeout=None)

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
        description=f"**Current Settings:**\n- Counting Enabled: `{countingData['enabled']}`\n- Counting Channel: `<#{countingData['channel']}>`\n- Current Number: `{countingData['number']}`\n- Highest Number: `{countingData.get('highestnumber', 0)}`\n- Warnings: `{countingData['warnings']}`\n- Last Counter: `{countingData['lastcounter']}`",
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
        title=f"{Emojis["Loading"] interaction.user.mention} Searching For {user}!",
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

@bot.tree.command(name="ai", description="Chat with an AI assistant.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ai(interaction: discord.Interaction, *, prompt: str):
    await interaction.response.defer(thinking=True)

    loading = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Getting AI Response For: {prompt}",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )

    await interaction.followup.send(embed=loading)
    
    user_id = str(interaction.user.id)
    username = interaction.user.name

    # Load or initialize user data
    user_data = AI_DB.get(user_id) or {"username": username, "user_messages": [], "ai_responses": []}
    user_data["username"] = username
    user_data["user_messages"].append(prompt)
    
    # Keep last 5 messages for context
    user_data["user_messages"] = user_data["user_messages"][-50:]
    user_data["ai_responses"] = user_data["ai_responses"][-50:]

    # System instructions for the AI
    messages_for_ai = [
        {
            "role": "system",
            "content": (
                f"You are a helpful Discord assistant chatting with {username}. "
                "Always respond in a single concise paragraph. "
                "Follow Discord TOS. Do not provide instructions for illegal activity. "
                "Stay safe, respectful, and friendly."
            )
        }
    ]

    # Include previous conversation
    for u_msg, a_msg in zip(user_data["user_messages"], user_data["ai_responses"]):
        messages_for_ai.append({"role": "user", "content": u_msg})
        messages_for_ai.append({"role": "assistant", "content": a_msg})

    # Add latest message
    messages_for_ai.append({"role": "user", "content": prompt})

    try:
        response = chatgpt.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for_ai
        )
        ai_reply = response.choices[0].message.content.strip()
    except Exception as e:
        ai_reply = f"⚠️ API error: {e}"

    # Save AI response
    user_data["ai_responses"].append(ai_reply)
    AI_DB.set(user_id, user_data)
    AI_DB.save()

    # Create embed
    embed = discord.Embed(
        title=f"💬 Chat with {username}",
        color=embedDB.get(user_id) or discord.Color.blue()
    )
    embed.add_field(name="🧍 You said:", value=prompt[:1024], inline=False)
    embed.add_field(name="🤖 AI replied:", value=ai_reply[:1024], inline=False)
    embed.set_footer(text=f"{MainURL} | Requested by {username}")

    await interaction.edit_original_response(embed=embed)

@bot.tree.command(name="google", description="Search Something On Google.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def google(interaction: discord.Interaction, query: str = "shapes.lol"):
    await interaction.response.defer(thinking=True)
    thinkingembed = discord.Embed(
        title=f"{Emojis["Loading"] interaction.user.mention} Searching Google For {query}",
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
                title=f"{Emojis["Loading"] interaction.user.mention} Searching For {user}'s Roblox profile!",
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

            rap_value = 0
            value_value = 0
            rolimons_last_online = None
            badge_last_online = None
            
            try:
                connector = aiohttp.TCPConnector(family=socket.AF_INET)
                async with aiohttp.ClientSession(connector=connector) as session:
                    rolimons_stats_url = f"https://api.rolimons.com/players/v1/playerinfo/{UserID}"
                    async with session.get(rolimons_stats_url, headers={'User-Agent': 'shapes.lol'}) as response:
                        if response.status == 200:
                            rolimons_stats_data = await response.json()
                            if rolimons_stats_data.get('success'):
                                rap_value = rolimons_stats_data.get('rap', 0) or 0
                                value_value = rolimons_stats_data.get('value', 0) or 0
                                rolimons_last_online = rolimons_stats_data.get('last_online')
                    
                    user_badges_url = f"https://badges.roblox.com/v1/users/{UserID}/badges?sortOrder=Desc&limit=10"
                    async with session.get(user_badges_url) as response:
                        if response.status == 200:
                            user_badges_result = await response.json()
                            if user_badges_result and user_badges_result.get('data'):
                                recent_badge = user_badges_result['data'][0]
                                badge_id = recent_badge.get('id')
                                
                                if badge_id:
                                    badge_awarded_url = f"https://badges.roblox.com/v1/users/{UserID}/badges/awarded-dates?badgeIds={badge_id}"
                                    async with session.get(badge_awarded_url) as badge_response:
                                        if badge_response.status == 200:
                                            badge_awarded_result = await badge_response.json()
                                            if badge_awarded_result and badge_awarded_result.get('data'):
                                                awarded_date = badge_awarded_result['data'][0].get('awardedDate')
                                                if awarded_date:
                                                    try:
                                                        dt = datetime.fromisoformat(awarded_date.replace('Z', '+00:00'))
                                                        badge_last_online = int(dt.timestamp())
                                                    except (ValueError, AttributeError):
                                                        pass
            except Exception as e:
                print(f"Error fetching Rolimons stats: {e}")

            rolimonsurl = f"https://rolimons.com/player/{UserID}"

            url = f"https://users.roblox.com/v1/users/{UserID}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                playerdata = response.json()
                Description = playerdata["description"]
                Banned = playerdata["isBanned"]
                user = playerdata["name"]
                JoinDate = playerdata["created"]
                created_timestamp = isotodiscordtimestamp(JoinDate)
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

            if UserID == 124767284:
                hasVerifiedBadge = True
            
            if hasVerifiedBadge:
                Username += " <:RobloxVerified:1416951927513677874>"

            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={UserID}&size=420x420&format=Png&isCircular=false"
            is_terminated = False
            avatar_image = None
            
            try:
                response = requests.get(avatar_url)
                response.raise_for_status()
                data = response.json()
                if data and data.get("data") and len(data["data"]) > 0:
                    avatar_image = data["data"][0].get("imageUrl")
                    if avatar_image and avatar_image.startswith("https://t7.rbxcdn.com"):
                        is_terminated = True
            except requests.exceptions.RequestException as e:
                print(f"Error fetching avatar: {e}")

            if is_terminated:
                Username = f":warning: [Banned] {Username}"

            url = f"https://api.ropro.io/getUserInfoTest.php?userid={UserID}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                RoProData = response.json()
                Discord = RoProData["discord"]
            except requests.exceptions.RequestException as e:
                print(f"Error fetching RoPro data for ID {UserID}: {e}")
                Discord = ""

            profileurl = f"https://www.roblox.com/users/{UserID}/profile"

            last_online_timestamp = None
            last_online_source = "Unknown"
            
            if badge_last_online and rolimons_last_online:
                last_online_timestamp = max(badge_last_online, rolimons_last_online)
                last_online_source = "Recent Activity"
            elif badge_last_online:
                last_online_timestamp = badge_last_online
                last_online_source = "Badge Activity"
            elif rolimons_last_online:
                last_online_timestamp = rolimons_last_online
                last_online_source = "Rolimons Data"

            formatted_last_online = "Unknown"
            if last_online_timestamp:
                try:
                    formatted_last_online = f"<t:{last_online_timestamp}:D>"
                except (ValueError, AttributeError):
                    formatted_last_online = "Unknown"

            view = discord.ui.View()
            if not is_terminated:
                view.add_item(discord.ui.Button(
                    label="Roblox Profile",
                    style=discord.ButtonStyle.link,
                    emoji="<:RobloxLogo:1416951004607418398>",
                    url=profileurl
            ))
            view.add_item(discord.ui.Button(
                label="View Rolimons",
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
            
            embed.add_field(name="RAP", value=f"[`{rap_value:,}`]({rolimonsurl})", inline=True)
            embed.add_field(name="Value", value=f"[`{value_value:,}`]({rolimonsurl})", inline=True)
            embed.add_field(name="Last Online", value=formatted_last_online, inline=True)
            
            if Discord != "":
                embed.add_field(
                    name="Discord (RoPro)",
                    value=f"```txt\n{Discord}\n```",
                    inline=False
                )
            
            embed.add_field(name="Username", value=user, inline=False)
            embed.add_field(name="ID", value=UserID, inline=False)
            embed.add_field(name="Terminated", value="True" if is_terminated else "False", inline=False)
            
            if created_timestamp:
                embed.add_field(name="Join Date", value=created_timestamp, inline=False)
            else:
                embed.add_field(name="Join Date", value="Unknown", inline=False)

            if avatar_image:
                embed.set_thumbnail(url=avatar_image)
                embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
                await interaction.edit_original_response(embed=embed, view=view)
                return
            else:
                failedembed5 = discord.Embed(
                    title=f"Failed To Retrieve {user}'s avatar!",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=failedembed5)
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
        print(f"An error occurred during the request: {e}")
        failedembed8 = discord.Embed(
            title=f":warning: {user} not found.",
            color=discord.Color.yellow()
        )
        await interaction.edit_original_response(embed=failedembed8)
        return
        
@bot.tree.command(name="britishuser", description="Check if a user has their language set to British")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def british_check(interaction: discord.Interaction, user_input: str):
    await interaction.response.defer(thinking=True)
    
    embed_color = embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    
    thinkingembed = discord.Embed(
        title=f"{Emojis["Loading"] interaction.user.mention} Checking if {user_input} is British!",
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
        title=f"{Emojis["Loading"] interaction.user.mention} Searching For {item_query}'s Item Information!",
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
        creator_target_id = item_data.get("creatorTargetId")
        favorite_count = item_data.get("favoriteCount", 0)
        lowest_price = item_data.get("lowestPrice", 0)
        is_purchasable = item_data.get("isPurchasable", False)
        item_type = item_data.get("itemType", "Asset")
        
        created_date = item_data.get("itemCreatedUtc")
        
        if creator_type == "Group" and creator_target_id == 5544706:
            creator_verified = True

        if creator_type == "User" and creator_target_id == 124767284:
            creator_verified = True
        
        if created_date:
            created_timestamp = isotodiscordtimestamp(created_date, "F")
        else:
            created_timestamp = "Unknown"
        
        updated_timestamp = created_timestamp

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
        embed.add_field(name="Favorites", value=f"{favorite_count:,}", inline=True)
        embed.add_field(name="Created", value=created_timestamp, inline=True)

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
        title=f"{Emojis["Loading"] interaction.user.mention} Searching For Group ID {group_id}!",
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

        if group_id == "5544706":
            group_verified = True
        
        owner_verified = False
        if owner_id:
            try:
                user_url = f"https://users.roblox.com/v1/users/{owner_id}"
                user_response = requests.get(user_url)
                user_response.raise_for_status()
                user_data = user_response.json()
                owner_verified = user_data.get("hasVerifiedBadge", False)
                if user_data.get("id") == 124767284:
                    owner_verified = True
            except requests.exceptions.RequestException as e:
                print(f"Error fetching owner data: {e}")

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
            emoji=Emojis["Roblox"]["logo"],
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

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="placeinfo", description="Get detailed information about a Roblox place")
@app_commands.describe(game_input="Roblox place ID or game URL")
async def placeinfo(interaction: discord.Interaction, game_input: str):
    await interaction.response.defer(thinking=True)
    
    thinkingembed = discord.Embed(
        title=f"{Emojis["Loading"] interaction.user.mention} Searching For Place Information!",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    await interaction.followup.send(embed=thinkingembed)

    try:
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        async with aiohttp.ClientSession(connector=connector) as session:
            place_id = None
            
            if "roblox.com/games/" in game_input:
                match = re.search(r'roblox\.com/games/(\d+)', game_input)
                if match:
                    place_id = match.group(1)
                else:
                    errorembed = discord.Embed(
                        title=":x: Invalid URL :x:",
                        description="Could not extract place ID from the URL",
                        color=discord.Color.red()
                    )
                    #errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
                    await interaction.edit_original_response(embed=errorembed)
                    return
            else:
                if not game_input.isdigit():
                    errorembed = discord.Embed(
                        title=":x: Invalid Input :x:",
                        description="Please provide a valid place ID or Roblox game URL",
                        color=discord.Color.red()
                    )
                    #errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
                    await interaction.edit_original_response(embed=errorembed)
                    return
                place_id = game_input
            
            universe_url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
            async with session.get(universe_url) as response:
                if response.status != 200:
                    errorembed = discord.Embed(
                        title=":x: API Error :x:",
                        description=f"Failed to fetch universe information (Status: {response.status})",
                        color=discord.Color.red()
                    )
                    #errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
                    await interaction.edit_original_response(embed=errorembed)
                    return
                
                universe_data = await response.json()
                universe_id = universe_data.get('universeId')
                
                if not universe_id:
                    errorembed = discord.Embed(
                        title=":x: Not Found :x:",
                        description="Could not find universe for this place ID",
                        color=discord.Color.red()
                    )
                    #errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
                    await interaction.edit_original_response(embed=errorembed)
                    return
            
            games_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
            async with session.get(games_url) as response:
                if response.status != 200:
                    errorembed = discord.Embed(
                        title=":x: API Error :x:",
                        description=f"Failed to fetch game details (Status: {response.status})",
                        color=discord.Color.red()
                    )
                    errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
                    await interaction.edit_original_response(embed=errorembed)
                    return
                
                games_data = await response.json()
                if not games_data.get('data') or len(games_data['data']) == 0:
                    errorembed = discord.Embed(
                        title=":x: Not Found :x:",
                        description="Could not find game details for this universe",
                        color=discord.Color.red()
                    )
                    errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
                    await interaction.edit_original_response(embed=errorembed)
                    return
                
                game_info = games_data['data'][0]
            
            name = game_info.get('name', 'Unknown')
            description = game_info.get('description', 'No description available')
            creator_id = game_info.get('creator', {}).get('id', 'Unknown')
            creator_name = game_info.get('creator', {}).get('name', 'Unknown')
            creator_type = game_info.get('creator', {}).get('type', 'User')
            current_players = game_info.get('playing', 0)
            visits = game_info.get('visits', 0)
            max_players = game_info.get('maxPlayers', 0)
            created = game_info.get('created', 'Unknown')
            updated = game_info.get('updated', 'Unknown')
            genre = game_info.get('genre', 'Unknown')
            favorites_count = game_info.get('favoritedCount', 0)
        
            created_timestamp = isotodiscordtimestamp(created, "F") if created != 'Unknown' else "Unknown"
            updated_timestamp = isotodiscordtimestamp(updated, "F") if updated != 'Unknown' else "Unknown"
            
            thumbnail_url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={universe_id}&size=512x512&format=Png&isCircular=false"
            thumbnail_image = None
            async with session.get(thumbnail_url) as response:
                if response.status == 200:
                    thumbnail_data = await response.json()
                    if thumbnail_data.get('data') and len(thumbnail_data['data']) > 0:
                        thumbnail_image = thumbnail_data['data'][0]['imageUrl']
            
            embed = discord.Embed(
                title=name,
                url=f"https://www.roblox.com/games/{place_id}/",
                description=description,
                color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
            )
        
            embed.add_field(name="Place ID", value=f"`{place_id}`", inline=True)
            embed.add_field(name="Universe ID", value=f"`{universe_id}`", inline=True)
            
            if creator_type.lower() == "user":
                creator_display = f"[{creator_name}](https://www.roblox.com/users/{creator_id}/profile)"
            else:
                creator_display = f"[{creator_name}](https://www.roblox.com/groups/{creator_id}/)"
            embed.add_field(name="Creator", value=creator_display, inline=True)

            embed.add_field(name="Visits", value=f"{visits:,}", inline=True)
            embed.add_field(name="Current Players", value=f"{current_players:,}", inline=True)
            embed.add_field(name="Max Players", value=f"{max_players}", inline=True)
            
            embed.add_field(name="Favorites", value=f"{favorites_count:,}", inline=True)
            embed.add_field(name="Genre", value=genre, inline=True)
            
            embed.add_field(name="Created", value=created_timestamp, inline=True)
            embed.add_field(name="Updated", value=updated_timestamp, inline=True)
            
            if description and description != "No description available":
                if len(description) > 1024:
                    description = description[:1021] + "..."
                if len(embed.fields) % 3 != 0:
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
                embed.add_field(name="Description", value=description, inline=False)
            
            if thumbnail_image:
                embed.set_thumbnail(url=thumbnail_image)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="View Game",
                style=discord.ButtonStyle.link,
                emoji=Emojis["Roblox"]["logo"],
                url=f"https://www.roblox.com/games/{place_id}/"
            ))
            
            embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
            await interaction.edit_original_response(embed=embed, view=view)
            
    except Exception as e:
        print(f"Error in placeinfo command: {e}")
        errorembed = discord.Embed(
            title=":x: Unexpected Error :x:",
            description=f"An error occurred while fetching place information: {str(e)}",
            color=discord.Color.red()
        )
        #errorembed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
        await interaction.edit_original_response(embed=errorembed)

async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=f":x: {title}",
        description=description,
        color=discord.Color.red()
    )
    #embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
    await interaction.followup.send(embed=embed)

async def get_badge_thumbnail(session: aiohttp.ClientSession, badge_id: str) -> Optional[str]:
    thumbnail_url = f"https://thumbnails.roblox.com/v1/badges/icons?badgeIds={badge_id}&size=150x150&format=Png"
    
    try:
        async with session.get(thumbnail_url) as response:
            if response.status == 200:
                thumbnail_data = await response.json()
                if thumbnail_data.get('data') and len(thumbnail_data['data']) > 0:
                    return thumbnail_data['data'][0].get('imageUrl')
    except Exception:
        pass
    return None

async def create_badge_embed(badge_data: dict, thumbnail_url: Optional[str], badge_id: str, 
                           start_time: float, requester: discord.User) -> discord.Embed:
    badge_id = badge_data.get('id', 'N/A')
    name = badge_data.get('name', 'Unknown')
    display_name = badge_data.get('displayName', name)
    description = badge_data.get('description') or badge_data.get('displayDescription') or "No description"
    
    statistics = badge_data.get('statistics', {})
    past_day_awarded = statistics.get('pastDayAwardedCount', 0)
    awarded_count = statistics.get('awardedCount', 0)
    win_rate = statistics.get('winRatePercentage', 0)
    
    created = badge_data.get('created', 'Unknown')
    updated = badge_data.get('updated', 'Unknown')
    
    awarding_universe = badge_data.get('awardingUniverse', {})
    universe_name = awarding_universe.get('name', 'Unknown')
    universe_id = awarding_universe.get('id', 'N/A')
    root_place_id = awarding_universe.get('rootPlaceId', 'N/A')
    
    embed_color = embedDB.get(f"{requester.id}") if embedDB.get(f"{requester.id}") else discord.Color.blue()
    
    embed = discord.Embed(
        title=f"Badge: {display_name}",
        color=embed_color,
        timestamp=datetime.now(),
        url=f"https://www.roblox.com/badges/{badge_id}"
    )
    
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    embed.add_field(name="Badge ID", value=f"`{badge_id}`", inline=True)
    embed.add_field(name="Internal Name", value=name, inline=True)
    embed.add_field(name="Enabled", value="Yes" if badge_data.get('enabled') else "No", inline=True)
    
    embed.add_field(name="Description", value=description, inline=False)
    
    embed.add_field(name="Awarded Today", value=f"{past_day_awarded:,}", inline=True)
    embed.add_field(name="Obtained Total", value=f"{awarded_count:,}", inline=True)
    embed.add_field(name="Win Rate", value=f"{win_rate}%", inline=True)
    
    created_timestamp = isotodiscordtimestamp(created)
    updated_timestamp = isotodiscordtimestamp(updated)
    
    if created_timestamp:
        embed.add_field(
            name="Created", 
            value=f"{created_timestamp} {created_timestamp})", 
            inline=True
        )
    else:
        embed.add_field(name="Created", value=created, inline=True)
    
    if updated_timestamp:
        embed.add_field(
            name="Last Updated", 
            value=f"<t:{updated_timestamp}:f> (<t:{updated_timestamp}:R>)", 
            inline=True
        )
    else:
        embed.add_field(name="Last Updated", value=updated, inline=True)
    
    if universe_id != 'N/A':
        universe_field = f"[{universe_name}](https://www.roblox.com/games/{root_place_id}/)"
        universe_field += f"\nUniverse ID: `{universe_id}`"
        if root_place_id != 'N/A':
            universe_field += f"\nPlace ID: `{root_place_id}`"
        
        embed.add_field(name="Awarding Universe", value=universe_field, inline=False)
    
    elapsed_time = asyncio.get_event_loop().time() - start_time
    embed.set_footer(text=f"Load time: {elapsed_time:.2f}s • Requested by {requester.display_name} | {MainURL}")
    
    return embed

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="badge", description="Get detailed information about a Roblox badge")
@app_commands.describe(badge_id="The ID of the Roblox badge")
async def badge_info(interaction: discord.Interaction, badge_id: str):
    await interaction.response.defer(thinking=True)
    start_time = asyncio.get_event_loop().time()
    
    thinkingembed = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching For Badge ID {badge_id}!",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    await interaction.followup.send(embed=thinkingembed)
    
    if not badge_id.isdigit():
        await send_error_embed(
            interaction,
            "Invalid Badge ID",
            "Please provide a valid numeric badge ID."
        )
        return
    
    connector = aiohttp.TCPConnector(family=socket.AF_INET)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            badge_url = f"https://badges.roblox.com/v1/badges/{badge_id}"
            
            async with session.get(badge_url) as response:
                if response.status == 404:
                    await send_error_embed(
                        interaction,
                        "Badge Not Found",
                        f"Could not find a badge with ID `{badge_id}`"
                    )
                    return
                elif response.status != 200:
                    await send_error_embed(
                        interaction,
                        "API Error",
                        f"Failed to fetch badge information (Status: {response.status})"
                    )
                    return
                
                badge_data = await response.json()
            
            thumbnail_url = await get_badge_thumbnail(session, badge_id)
            
            embed = await create_badge_embed(badge_data, thumbnail_url, badge_id, start_time, interaction.user)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="View Badge",
                style=discord.ButtonStyle.link,
                emoji="<:RobloxLogo:1416951004607418398>",
                url=f"https://www.roblox.com/badges/{badge_id}"
            ))
            
            await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            await send_error_embed(interaction, "Unexpected Error", f"An error occurred: {str(e)}")

@bot.tree.command(name="autorole", description="Set a role to be automatically given to members")
@app_commands.default_permissions(administrator=True)
@commands.bot_has_permissions(add_reactions=True, moderate_members=True, read_message_history=True, view_channel=True, send_messages=True)
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(
    role="The role to automatically assign to members",
    enable="Whether to enable or disable autorole (default: True)"
)
async def autorole(interaction: discord.Interaction, role: discord.Role, enable: bool = True):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
        return
    
    autorole_data = {"role_id": role.id, "enabled": enable}
    autoroleDB.set(f"{interaction.guild.id}", autorole_data)
    autoroleDB.save()
    
    class AutoroleView(discord.ui.View):
        @discord.ui.button(label="Assign to Existing Members", style=discord.ButtonStyle.primary)
        async def assign_existing(self, interaction: discord.Interaction, button: discord.ui.Button):
            count = 0
            for member in interaction.guild.members:
                if not member.bot and role not in member.roles:
                    try:
                        await member.add_roles(role)
                        count += 1
                    except:
                        pass
            await interaction.response.send_message(f"Assigned {role.mention} to {count} existing members", ephemeral=True)
    
    status = "enabled" if enable else "disabled"
    await interaction.response.send_message(
        f"Autorole {status} for {role.mention}. Assign to existing members?", 
        view=AutoroleView(), 
        ephemeral=True
    )

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Counting Commands", description="Counting game and settings"),
            discord.SelectOption(label="User Settings", description="Personal bot settings"),
            discord.SelectOption(label="Roblox Commands", description="Roblox user and item information"),
            discord.SelectOption(label="Utility Commands", description="General utility commands"),
            discord.SelectOption(label="Context Menu Commands", description="Right-click context commands")
        ]
        super().__init__(placeholder="Choose a command category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed_color = embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
        
        if category == "Counting Commands":
            embed = discord.Embed(title="Counting Commands", color=embed_color)
            embed.add_field(name="Commands", value=
                "• /counting - Counting in a specific channel", inline=False)
                
        elif category == "User Settings":
            embed = discord.Embed(title="User Settings", color=embed_color)
            embed.add_field(name="Commands", value=
                "• /settings - Customize your personal bot settings", inline=False)
                
        elif category == "Roblox Commands":
            embed = discord.Embed(title="Roblox Commands", color=embed_color)
            embed.add_field(name="Commands", value=
                "• /robloxinfo - Get detailed Roblox user information\n"
                "• /roblox2discord - Find a Roblox user's Discord\n"
                "• /britishuser - Check if user is british\n"
                "• /iteminfo - Get Roblox item information\n"
                "• /groupinfo - Get Roblox group information\n"
                "• /placeinfo - Get Roblox place/game information\n"
                "• /badge - Get Roblox badge information", inline=False)
                
        elif category == "Utility Commands":
            embed = discord.Embed(title="Utility Commands", color=embed_color)
            embed.add_field(name="Commands", value=
                "• /ping - Check bot latency and connection\n"
                "• /invite - Get bot invite link\n"
                "• /google - Search something on Google\n"
                "• /status - Check shapes.lol status\n"
                "• /userinstalls - Get user installation count\n"
                "• /servercount - Get server count\n"
                "• /spookpfp - Get profile picture from spook.bio", inline=False)
                
        elif category == "Context Menu Commands":
            embed = discord.Embed(title="Context Menu Commands", color=embed_color)
            embed.add_field(name="Commands", value=
                "• Right-click a user → Apps → sayhitouser - Say hello to a user\n"
                "• Right-click a user → Apps → discord2spook - Get user's spook.bio profile\n"
                "• Right-click a message → Apps → google - Search message content on Google", inline=False)
        
        embed.set_footer(text="Use slash commands (/) to interact")
        await interaction.response.edit_message(embed=embed, ephemeral=True)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(HelpDropdown())

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="help", description="Get help with all available commands")
async def help_command(interaction: discord.Interaction):
    """Display help information for all bot commands"""
    
    embed_color = embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    
    embed = discord.Embed(
        title="Bot Help & Commands",
        description="Use the dropdown menu below to browse commands by category.",
        color=embed_color
    )
    
    view = HelpView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="countingleaderboard", description="View the counting leaderboard website")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def countingleaderboard(interaction: discord.Interaction):
    """Send the counting leaderboard website link"""
    
    embed = discord.Embed(
        title="Counting Leaderboard",
        description=f"[Click here to view the counting leaderboard](https://shapes.lol/counting/leaderboard/)",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    embed.set_footer(text=f"Requested By {interaction.user.name} | {MainURL}")
    
    await interaction.response.send_message(embed=embed)

class BadgeService:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
    
    async def get_user_id(self, user_input: str) -> Optional[str]:
        if user_input.isdigit():
            return user_input
        return await self._get_id_from_username(user_input)
    
    async def _get_id_from_username(self, username: str) -> Optional[str]:
        url = "https://users.roblox.com/v1/usernames/users"
        try:
            async with self.session.post(url, json={"usernames": [username]}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        return str(data["data"][0]["id"])
        except Exception:
            pass
        return None
    
    async def get_username(self, user_id: str) -> Optional[str]:
        url = f"https://users.roblox.com/v1/users/{user_id}"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("name")
        except Exception:
            pass
        return None
    
    async def get_user_badges(self, user_id: str, limit: int = 10) -> tuple[list, int]:
        badges_url = f"https://badges.roblox.com/v1/users/{user_id}/badges?sortOrder=Desc&limit={limit}"
        
        async with self.session.get(badges_url) as response:
            if response.status != 200:
                return [], response.status
            
            data = await response.json()
            return data.get('data', []), response.status
    
    async def get_awarded_dates(self, user_id: str, badge_ids: list) -> Dict[int, str]:
        if not badge_ids:
            return {}
            
        awarded_dates_url = f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates?badgeIds={','.join(map(str, badge_ids))}"
        
        try:
            async with self.session.get(awarded_dates_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {item['badgeId']: item.get('awardedDate') for item in data.get('data', [])}
        except Exception:
            pass
        return {}
    
    async def get_badge_thumbnail(self, badge: Dict[str, Any]) -> Optional[str]:
        icon_image_id = badge.get('iconImageId') or badge.get('displayIconImageId')
        if not icon_image_id:
            return None
            
        icon_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={icon_image_id}&size=150x150&format=Png&isCircular=false"
        
        try:
            async with self.session.get(icon_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data') and len(data['data']) > 0:
                        return data['data'][0]['imageUrl']
        except Exception:
            pass
        return None

class BadgeFormatter:
    @staticmethod
    def parse_iso_timestamp(timestamp_str: Optional[str]) -> Optional[int]:
        if not timestamp_str:
            return None
            
        try:
            timestamp_str = timestamp_str.split('.')[0]
            
            if timestamp_str.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_str[:-1]).replace(
                    tzinfo=datetime.timezone.utc
                )
            else:
                if '+' not in timestamp_str and 'Z' not in timestamp_str:
                    timestamp_str += '+00:00'
                dt = datetime.fromisoformat(timestamp_str)
            
            return int(dt.timestamp())
        except (ValueError, AttributeError, TypeError):
            return None
    
    @staticmethod
    def format_creator_info(creator: Dict[str, Any]) -> str:
        creator_name = creator.get('name', 'Unknown')
        creator_type = creator.get('type', 'User')
        creator_id = creator.get('id')
        
        if not creator_id:
            return creator_name
            
        if creator_type.lower() == 'user':
            return f"[{creator_name}](https://www.roblox.com/users/{creator_id}/profile)"
        else:
            return f"[{creator_name}](https://www.roblox.com/groups/{creator_id}/)"
    
    @staticmethod
    def format_awarder_info(awarder: Dict[str, Any]) -> str:
        awarder_type = awarder.get('type', 'Unknown')
        awarder_id = awarder.get('id')
        
        if not awarder_id:
            return "Unknown"
            
        if awarder_type.lower() == 'place':
            return f"[Place #{awarder_id}](https://www.roblox.com/games/{awarder_id}/)"
        else:
            return f"{awarder_type} #{awarder_id}"

class BadgesView(discord.ui.View):
    def __init__(self, badges: list, username: str, user_id: str, requester: discord.User, 
                 start_time: float, badge_service: BadgeService):
        super().__init__(timeout=120)
        self.badges = badges
        self.current_page = 0
        self.username = username
        self.user_id = user_id
        self.requester = requester
        self.start_time = start_time
        self.badge_service = badge_service
        self.message = None
        self.thumbnail_cache = {}
        self.update_buttons()
    
    async def preload_thumbnails(self):
        for i, badge in enumerate(self.badges):
            thumbnail_url = await self.badge_service.get_badge_thumbnail(badge)
            if thumbnail_url:
                self.thumbnail_cache[i] = thumbnail_url
    
    async def create_embed(self) -> discord.Embed:
        badge = self.badges[self.current_page]
        
        embed = discord.Embed(
            title=f"{self.username}'s Recent Badges",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
            url=f"https://www.roblox.com/users/{self.user_id}/badges"
        )
        
        thumbnail_url = self.thumbnail_cache.get(self.current_page)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        
        badge_name = badge.get('displayName') or badge.get('name', 'Unknown Badge')
        badge_description = badge.get('displayDescription') or badge.get('description', 'No description')
        badge_id = badge.get('id', 'N/A')
        
        embed.add_field(name="Badge Name", value=badge_name, inline=False)
        embed.add_field(name="Description", value=badge_description or "No description", inline=False)
        embed.add_field(name="Badge ID", value=f"`{badge_id}`", inline=True)
        
        awarded_date = badge.get('awardedDate')
        if awarded_date:
            unix_timestamp = BadgeFormatter.parse_iso_timestamp(awarded_date)
            if unix_timestamp:
                embed.add_field(
                    name="Awarded Date", 
                    value=f"<t:{unix_timestamp}:f> (<t:{unix_timestamp}:R>)", 
                    inline=False
                )
            else:
                embed.add_field(name="Awarded Date", value=awarded_date, inline=False)
        
        creator = badge.get('creator', {})
        creator_text = BadgeFormatter.format_creator_info(creator)
        embed.add_field(name="Creator", value=creator_text, inline=True)
        
        awarder = badge.get('awarder', {})
        awarder_text = BadgeFormatter.format_awarder_info(awarder)
        embed.add_field(name="Awarded By", value=awarder_text, inline=True)
        
        stats = badge.get('statistics', {})
        awarded_count = stats.get('awardedCount', 0)
        win_rate = stats.get('winRatePercentage', 0)
        
        embed.add_field(name="Times Awarded", value=f"{awarded_count:,}", inline=True)
        embed.add_field(name="Win Rate", value=f"{win_rate}%", inline=True)
        
        elapsed_time = asyncio.get_event_loop().time() - self.start_time
        embed.set_footer(
            text=f"Badge {self.current_page + 1}/{len(self.badges)} • Load time: {elapsed_time:.2f}s • Requested by {self.requester.display_name}"
        )
        
        return embed
        
    def update_buttons(self):
        self.clear_items()
        
        if self.current_page > 0:
            previous_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⬅️", custom_id="previous")
            previous_btn.callback = self.previous_callback
            self.add_item(previous_btn)
            
        if self.current_page < len(self.badges) - 1:
            next_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="➡️", custom_id="next")
            next_btn.callback = self.next_callback
            self.add_item(next_btn)
        
        current_badge = self.badges[self.current_page]
        badge_id = current_badge.get('id')
        if badge_id:
            link_btn = discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="View Badge",
                url=f"https://www.roblox.com/badges/{badge_id}"
            )
            self.add_item(link_btn)
    
    async def _handle_navigation(self, interaction: discord.Interaction, direction: int):
        if interaction.user != self.requester:
            await interaction.response.send_message("You can't interact with this command!", ephemeral=True)
            return
        
        self.current_page += direction
        embed = await self.create_embed()
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def previous_callback(self, interaction: discord.Interaction):
        await self._handle_navigation(interaction, -1)
    
    async def next_callback(self, interaction: discord.Interaction):
        await self._handle_navigation(interaction, 1)
    
    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.style != discord.ButtonStyle.link:
                item.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass

async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="recentbadges", description="Get a user's most recently earned Roblox badges")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user_input="Roblox username or user ID")
async def recent_badges(interaction: discord.Interaction, user_input: str):
    await interaction.response.defer()
    
    thinkingembed = discord.Embed(
        title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching For {user_input}'s Recent Badges!",
        color=embedDB.get(f"{interaction.user.id}") if embedDB.get(f"{interaction.user.id}") else discord.Color.blue()
    )
    await interaction.followup.send(embed=thinkingembed)
    
    start_time = asyncio.get_event_loop().time()
    
    connector = aiohttp.TCPConnector(family=socket.AF_INET)
    async with aiohttp.ClientSession(connector=connector) as session:
        badge_service = BadgeService(session)
        
        try:
            user_id = await badge_service.get_user_id(user_input)
            if not user_id:
                await send_error_embed(
                    interaction, 
                    "User Not Found",
                    f"Could not find a Roblox user with the name or ID `{user_input}`"
                )
                return
            
            username = await badge_service.get_username(user_id)
            if not username:
                await send_error_embed(
                    interaction, 
                    "User Not Found",
                    f"Could not find a Roblox user with ID `{user_id}`"
                )
                return
            
            badges, status_code = await badge_service.get_user_badges(user_id)
            
            if status_code == 403:
                embed = discord.Embed(
                    title=f"{username}'s Recent Badges",
                    description="❌ This user's inventory is private. Badges cannot be viewed.",
                    color=discord.Color.orange(),
                    timestamp=interaction.created_at,
                    url=f"https://www.roblox.com/users/{user_id}/profile"
                )
                embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                await interaction.edit_original_response(embed=embed)
                return
            elif status_code != 200:
                await send_error_embed(
                    interaction,
                    "API Error",
                    f"Failed to fetch badges (Status: {status_code})"
                )
                return
            
            if not badges:
                embed = discord.Embed(
                    title=f"{username}'s Recent Badges",
                    description="This user has no badges.",
                    color=discord.Color.blue(),
                    timestamp=interaction.created_at,
                    url=f"https://www.roblox.com/users/{user_id}/profile"
                )
                elapsed_time = asyncio.get_event_loop().time() - start_time
                embed.set_footer(text=f"Load time: {elapsed_time:.2f}s • Requested by {interaction.user.display_name}")
                await interaction.edit_original_response(embed=embed)
                return
            
            badge_ids = [badge['id'] for badge in badges]
            awarded_dates = await badge_service.get_awarded_dates(user_id, badge_ids)
            
            for badge in badges:
                badge_id = badge['id']
                badge['awardedDate'] = awarded_dates.get(badge_id)
            
            view = BadgesView(badges, username, user_id, interaction.user, start_time, badge_service)
            await view.preload_thumbnails()
            embed = await view.create_embed()
            view.update_buttons()
            message = await interaction.edit_original_response(embed=embed, view=view)
            view.message = message
            
        except asyncio.TimeoutError:
            await send_error_embed(interaction, "Timeout Error", "The request timed out while fetching badge data.")
        except aiohttp.ClientError as e:
            await send_error_embed(interaction, "Network Error", f"Failed to connect to Roblox API: {str(e)}")
        except Exception as e:
            await send_error_embed(interaction, "Unexpected Error", f"An unexpected error occurred: {str(e)}")
    
# === Flask Runner in Thread ===
def run_flask():
    port = int(os.environ.get("PORT", 13455))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)

# === Run Bot + Flask Webserver ===
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(token)
