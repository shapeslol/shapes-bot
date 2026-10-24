# Shapes (Yapper bot)

The shapes.lol bot, running on [Yapper](https://www.yapper.website/developers) with `yapper.py`.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in YAPPER_BOT_TOKEN and the rest
python main.py
```

The web server listens on **port 5004** (`PORT` to change it). Open `/` and log in with `ADMIN_KEY` to see servers,
channels, recent messages, and to send messages as the bot. `/commands`, `/botinfo`, `/count/servers`, `/count/users`,
`/clb` and `/mutuals` are public JSON like before; `/api/*` is admin-only JSON.

## Storage

Data lives in Cloudflare Workers KV (`cfstore.py`): create a KV namespace, then set `CLOUDFLARE_API_TOKEN`,
`CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_KV_NAMESPACE_ID`. Without them the bot falls back to local `.json` files.
To copy old data across, run `python migrate_pickledb.py`.

## Files

- `main.py`: commands, events, web server
- `yshim.py`: a small discord.py-shaped layer on top of `yapper.py` (embeds, buttons, command arguments)
- `cfstore.py`: Cloudflare KV storage with a pickledb-style API
- `migrate_pickledb.py`: one-time import of the old `.db` files
