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
from datetime import datetime, timezone
from discord import app_commands
import requests
from discord.ext import commands
from discord.gateway import DiscordWebSocket, _log
from discord.ext.commands import Bot
from flask import Flask, render_template_string, request, redirect, url_for, session

# === Hardcoded Admin Key (change this!) ===
ADMIN_KEY = "lc1220"

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
owner = "sl.ip"
co_owner = "<@481295611417853982>"
MainURL = "https://shapes.lol"

try:
    with open('TOKEN.txt', 'r') as f:
        token = f.read()
except FileNotFoundError:
    print("Error: The file 'TOKEN' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")
# === Flask App Setup ===
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecret")

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
    <a href="https://dsc.gg/spookbio" target="_blank" rel="noopener" class="presence-button">
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

#bot = commands.Bot(command_prefix="/", intents=intents)
bot = MyBot(command_prefix="/", intents=discord.Intents.all())
#tree = app_commands.CommandTree(bot)

# === Background task to update cached guilds every 2 minutes ===
async def update_guild_cache():
    global cached_guilds
    while True:
        await bot.tree.sync()
        cached_guilds = list(bot.guilds)
        print(f"[SYSTEM] Watching {len(cached_guilds)} guilds! Updated List At {time.strftime('%X')}")
        await bot.change_presence(activity=discord.CustomActivity(name=":link: spook.bio/discord"))
        await asyncio.sleep(5)
        if len(bot.guilds) == 1:
            print(bot.guilds[0].name)
            #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=bot.guilds[0].name))
        else:
            print(f"Watching {len(bot.guilds)} Servers")
            #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers"))

        cached_guilds = []
        await asyncio.sleep(30)

# === Bot Events ===
@bot.event
async def on_ready():
    global bot_ready
    bot_ready = True
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")
    await bot.change_presence(activity=discord.CustomActivity(name="🔗 spook.bio/discord"))
    if len(bot.guilds) == 1:
        print(bot.guilds[0].name)
        #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=bot.guilds[0].name))
    else:
        print(f"Watching {len(bot.guilds)} Servers")
        #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers"))

    # Start the cache updater task
    MyBot(command_prefix="/", intents=discord.Intents.all())
    bot.loop.create_task(update_guild_cache())

def restartbot():
    print("Bot Restarting.")
    os.execv(sys.executable, ["python3 main.py =)"])
    os.kill(os.getpid(), signal.SIGINT)


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

# === Commands ===
@bot.tree.command(name="status", description=f"Get the {MainURL} status")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"[shapes.lol Status Page](https://spookbio.statuspage.io)")

@bot.tree.command(name="stop", description="Stop the bot.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def stop(interaction: discord.Interaction):
    if interaction.user.name == {owner} or {co_owner}:
        await interaction.response.send_message(":white_check_mark: Shutdown Successfully!", ephemeral=False)
        await bot.close()
        print("Bot Stopped.")
        sys.exit("Bot Stopped.")
    else:
        await interaction.response.send_message(f"Only {owner}, and {co_owner} can use this command.", ephemeral=True)

@bot.tree.command(name="restart", description="Restart the bot.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def restart(interaction: discord.Interaction):
    if interaction.user.name == {owner} or {co_owner}:
        await interaction.response.send_message(":white_check_mark: Restarted Successfully!!", ephemeral=False)
        restartbot()
    else:
        await interaction.response.send_message(f"Only {owner}, and {co_owner} can use this command.", ephemeral=True)

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
    url = f"https://prp.bio/discord/{user.name}"
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

@bot.tree.command(name="robloxinfo", description="Get a Roblox user's profile information.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def robloxinfo(interaction: discord.Interaction, user: str = "Roblox"):
    
    print(f"Searching For {user}'s profile")
    await interaction.response.defer(thinking=True)
    thinkingembed = discord.Embed(
                title=f"<a:loading:1416950730094542881> {interaction.user.mention} Searching For {user}'s Roblox Profile!",
                color=discord.Color.blue()
            )
    await interaction.followup.send(embed=thinkingembed)

    url = "https://users.roblox.com/v1/usernames/users"
    # print(f"Fetching Data From {url}")
    
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
            print(f"UserInfo: {userinfo}")

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
                await interaction.edit_original_response("Error retrieving description")
                return

            if Display == user:
                Username = Display
            else:
                Username = f"{Display} (@{user})"

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
                print(f"Error fetching ropro data for ID {UserID}: {e}")
                await interaction.edit_original_response(f"Error retrieving Discord User from {url}")
                return

            profileurl = f"https://www.roblox.com/users/{UserID}/profile"
            rolimonsurl = f"https://rolimons.com/player/{UserID}"

            # --- Create link buttons ---
            view = discord.ui.View()
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
                color=discord.Color.blue()
            )
            if Discord != "":
                embed.add_field(name="Discord (RoPro)", value=f"```{Discord}```", inline=False)
            
            embed.add_field(name="Username", value=user, inline=False)
            embed.add_field(name="UserID", value=UserID, inline=False)
            embed.add_field(name="Join Date", value=RobloxJoinDate_DiscordTimestamp, inline=False)

            # Get avatar headshot
            url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={UserID}&size=420x420&format=Png&is=false"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                if data and data.get("data") and len(data["data"]) > 0:
                    HeadShot = data["data"][0].get("imageUrl")
                    embed.set_author(name=user, url=profileurl, icon_url=HeadShot)
                    print(data)
                else:
                    print(f"Error fetching avatar headshot: {e}")
                    await interaction.edit_original_response(f"Failed To Retrieve {user}'s Headshot!")
                    return
            except requests.exceptions.RequestException as e:
                print(f"Error fetching avatar headshot: {e}")
                await interaction.edit_original_response(f"Failed To Retrieve {user}'s Headshot!")
                return

            # Get avatar bust
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
                    await interaction.edit_original_response(f"Failed To Retrieve {user}'s Avatar!")
                    return
            except requests.exceptions.RequestException as e:
                print(f"Error fetching avatar Avatar: {e}")
                await interaction.edit_original_response(f"Failed To Retrieve {user}'s Avatar!")
                return
        else:
            print(f"{user} not found.")
            await interaction.edit_original_response(f"{user} not found.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        await interaction.edit_original_response(f"An error occurred during the API request: {e}")
        return

# === Flask Runner in Thread ===
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)

# === Run Bot + Flask Webserver ===
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(token)