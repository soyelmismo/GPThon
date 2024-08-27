import os

from dotenv import load_dotenv

from bot.src.logs import logger

load_dotenv()

# parse environment variables
env = {key: os.getenv(key).split(',') if os.getenv(key) else [] for key in os.environ}

# Variables
session_name = str(env.get('SESSION_NAME', [''])[0])
api_id = int(env.get('API_ID', [''])[0])
error_report_channel_id = int(env.get('ERROR_REPORT_CHANNEL_ID', [''])[0])
error_report_channel_thread = int(env.get('ERROR_REPORT_CHANNEL_THREAD', [''])[0])

api_hash = str(env.get('API_HASH', [''])[0])
bot_token = str(env.get('TELEGRAM_TOKEN', [''])[0])

proxy_raw = env.get('API_TUNNEL', [None])[0]
apisproxy=proxy_raw
#apisproxy = {proxy_raw.split("://")[0] + "://": proxy_raw} if proxy_raw is not None else None
#if apisproxy:
#    apisproxy = next(iter(apisproxy.values()))

logger.info(f"ETH: 0x69b81AaE4e93bC5432dD2eFF320c4B43721419c9")

openai_style_apis = {}

#roleplay_enabled = False
#if openai_style_apis.get("apis_roleplay.json"):
#    roleplay_enabled = True

