import tweepy
import requests
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fastapi import FastAPI
import uvicorn

# Load environment variables
load_dotenv()

# Twitter API credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

# Twitch API credentials
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_API_BASE = "https://api.twitch.tv/helix/"

# Cache File Path
CACHE_FILE = "retweeted_cache.json"

# Initialize Retweeted Cache
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        retweeted_cache = set(json.load(f))
else:
    retweeted_cache = set()

# Authenticate Twitter API using OAuth1 for retweets
auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
)
api = tweepy.API(auth)

# Web server setup
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Running", "message": "Twitter/Twitch Bot is Active!"}

@app.get("/status")
def bot_status():
    return {
        "twitter_users": ["StableRonaldo", "LacyHimself"],
        "twitch_users": ["stableronaldo", "Lacy"],
        "last_checked": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

def get_twitch_token():
    response = requests.post(TWITCH_AUTH_URL, params={
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    })
    response.raise_for_status()
    return response.json()["access_token"]

TWITCH_TOKEN = get_twitch_token()
twitch_headers = {
    'Client-ID': TWITCH_CLIENT_ID,
    'Authorization': f'Bearer {TWITCH_TOKEN}'
}

async def auto_refresh_token():
    while True:
        await asyncio.sleep(3300)
        global TWITCH_TOKEN
        TWITCH_TOKEN = get_twitch_token()
        print("🔑 Twitch Token Refreshed!")

async def check_live_status(usernames):
    try:
        response = requests.get(f"{TWITCH_API_BASE}streams", headers=twitch_headers, params={"user_login": usernames})
        response.raise_for_status()
        streams = response.json().get("data", [])

        for stream in streams:
            message = f"🚀 {stream['user_name']} is now LIVE! Playing {stream['game_name']} \nWatch: https://twitch.tv/{stream['user_name']}"
            api.update_status(message)
            print("Tweeted:", message)
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] Twitch Error: {e}")

async def bot_loop():
    clan_twitch_users = ["stableronaldo", "Lacy"]
    while True:
        await check_live_status(clan_twitch_users)
        print(f"✅ Checked Twitch Live Status at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        await asyncio.sleep(300)  # Run every 5 minutes

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_refresh_token())  # Auto-refresh Twitch token
    loop.create_task(bot_loop())  # Start bot loop
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))  # Start FastAPI
