import os
from pathlib import Path
from json import load
from dotenv import load_dotenv

from bot.src.logs import logger
from io import BytesIO

load_dotenv()

# parse environment variables
env = {key: str(os.getenv(key)).split(',') if os.getenv(key) else [] for key in os.environ}

# Variables

bot_name = str(env.get('BOT_NAME_COMMAND', ['hey'])[0]).lower().strip()

command_chat = str(env.get('CHAT_COMMAND', ['/ask'])[0]).lower().strip()
command_image = str(env.get('IMAGE_COMMAND', ['/img'])[0]).lower().strip()
command_stt = str(env.get('STT_COMMAND', ['/stt'])[0]).lower().strip()


exclusive_api_name = str(env.get('EXCLUSIVE_API_NAME', [''])[0])

exclusive_api_chat_ids = env.get('EXCLUSIVE_API_WHITELIST', [])

blacklist_chat_ids = env.get('BLACKLIST_CHAT_ID', [])
whitelist_chat_ids = env.get('WHITELIST_CHAT_ID', [])

default_chat_model = env.get('DEFAULT_CHAT_MODEL', ['gpt-4o'])[0]
default_roleplay_model = env.get('DEFAULT_ROLEPLAY_MODEL', ['gpt-3.5-turbo'])[0]
max_input_tokens = int(env.get('MAX_INPUT_TOKENS', [4096])[0])
max_total_tokens = int(env.get('MAX_TOTAL_TOKENS', [8000])[0])

default_stt_model = env.get('DEFAULT_STT_MODEL', ['whisper-large-v3'])[0]
default_img_model = env.get('DEFAULT_IMAGE_MODEL', ['dall-e-3'])[0]
default_vision_model = env.get('DEFAULT_VISION_MODEL', ['chatgpt-4o-latest'])[0]
text_improve_model = env.get('TEXT_IMPROVE_MODEL', [False])[0]


api_id = int(env.get('API_ID', [''])[0])

session_name = str(env.get('SESSION_NAME', [''])[0])
error_report_channel_id = int(env.get('ERROR_REPORT_CHANNEL_ID', [''])[0])
error_report_channel_thread = int(env.get('ERROR_REPORT_CHANNEL_THREAD', [''])[0])

api_hash = str(env.get('API_HASH', [''])[0])
bot_token = str(env.get('TELEGRAM_TOKEN', [''])[0])

proxy_raw = env.get('API_TUNNEL', [None])[0]
apisproxy=proxy_raw
#apisproxy = {proxy_raw.split("://")[0] + "://": proxy_raw} if proxy_raw is not None else None
#if apisproxy:
#    apisproxy = next(iter(apisproxy.values()))

logger.info("ETH: 0x69b81AaE4e93bC5432dD2eFF320c4B43721419c9")

openai_style_apis = {}

basepath = Path(__file__).resolve().parents[1]
logger.debug(f'Base path: {basepath}')
apis_files = os.listdir(Path(f'{basepath}/resources/apis'))
logger.debug(f'apis_files: {basepath}')
    
available_api_json_files = [file for file in apis_files if file.endswith(".json")]
for fetcher in available_api_json_files:
    with open(basepath / "resources" / "apis" / fetcher, "r", encoding="utf-8") as infile:
        openai_style_apis[fetcher] = load(infile)

roleplay_enabled = False
if openai_style_apis.get("apis_roleplay.json"):
    roleplay_enabled = True

with open(basepath / "resources" / "prompts.json", "r", encoding="utf-8") as infile:
    bot_prompts = load(infile)

img_styles = {}
img_styles_txt = None
styles_str = None
with open(basepath / "resources" / "img_styles.json", "r", encoding="utf-8") as infile:
    img_styles = load(infile)
    img_styles_txt = BytesIO()
    img_styles_txt.name = '🎨👗.txt'
    styles_str = "\n".join(f"- {key}" for key in img_styles.keys())
    
    img_styles_txt.write(styles_str.encode('utf-8'))
    img_styles_txt.seek(0)
    logger.info(f"Image styles: {len(img_styles)}")
