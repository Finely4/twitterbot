import tweepy
import requests
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

def get_twitch_token():
    response = requests.post(TWITCH_AUTH_URL, params={
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    })
    response.raise_for_status()
    return response.json()["access_token"]

async def refresh_twitch_token():
    global TWITCH_TOKEN
    TWITCH_TOKEN = get_twitch_token()
    print("🔑 Twitch Token Refreshed!")

TWITCH_TOKEN = get_twitch_token()
twitch_headers = {
    'Client-ID': TWITCH_CLIENT_ID,
    'Authorization': f'Bearer {TWITCH_TOKEN}'
}

async def auto_refresh_token():
    """ Refresh Twitch token every 55 minutes """
    while True:
        await asyncio.sleep(3300)
        await refresh_twitch_token()

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
        await refresh_twitch_token()

async def check_twitter_updates(usernames):
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    for user in usernames:
        try:
            user_data = api.get_user(screen_name=user)
            if not user_data:
                print(f"[{datetime.now()}] User '{user}' not found.")
                continue

            tweets = api.user_timeline(screen_name=user, count=1, tweet_mode="extended")
            
            if tweets:
                tweet = tweets[0]
                tweet_id = str(tweet.id)
                tweet_time = tweet.created_at

                if tweet_id not in retweeted_cache and tweet_time > one_hour_ago:
                    api.retweet(tweet_id)
                    retweeted_cache.add(tweet_id)
                    await save_cache()
                    print(f"✅ Retweeted: {tweet.full_text}")
                    await asyncio.sleep(5)
                else:
                    print(f"❌ Skipped Old Tweet: {tweet.full_text}")

            await asyncio.sleep(10)  # Wait between users (Prevent 429)

        except tweepy.TweepyException as e:
            await handle_rate_limit(e)
        except Exception as e:
            print(f"[{datetime.now()}] Unexpected Error: {e}")

async def handle_rate_limit(e):
    """ Handle Twitter API rate limits with exponential backoff """
    if hasattr(e, "response") and e.response is not None and e.response.status_code == 429:
        reset_time = int(e.response.headers["x-rate-limit-reset"])
        wait_time = max(0, (datetime.utcfromtimestamp(reset_time) - datetime.utcnow()).seconds)
        print(f"🚫 Rate limit exceeded. Sleeping for {wait_time} seconds...")
        await asyncio.sleep(wait_time)

async def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(list(retweeted_cache), f)

async def main():
    clan_twitch_users = ["stableronaldo", "Lacy"]
    clan_twitter_users = ["StableRonaldo", "LacyHimself"]
    cooldown = 300

    asyncio.create_task(auto_refresh_token())  # Auto-refresh Twitch token

    while True:
        try:
            await check_live_status(clan_twitch_users)
            await check_twitter_updates(clan_twitter_users)
            print(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checked all clan members. Waiting {cooldown // 60} minutes...")
            await asyncio.sleep(cooldown)
        except tweepy.TweepyException as e:
            await handle_rate_limit(e)
        except Exception as e:
            print(f"[{datetime.now()}] Bot Error: {e}")
            cooldown += 300
            await asyncio.sleep(cooldown)

if __name__ == "__main__":
    print("🚀 Starting Bot...")
    asyncio.run(main())
