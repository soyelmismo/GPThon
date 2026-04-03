import os
from pathlib import Path
from json import load
from dotenv import load_dotenv

from bot.src.logs import logger



load_dotenv()

# parse environment variables
env = {key: str(os.getenv(key)).split(',') if os.getenv(key) else [] for key in os.environ}

valkey_enabled = str(env.get('ENABLE_VALKEY', ['True'])[0]).lower().strip() == 'true'

valkey_uri = str(env.get('VALKEY_URI', ['127.0.0.1:6379'])[0]).strip()
valkey_user = str(env.get('VALKEY_USER', [''])[0]).strip()
valkey_password = str(env.get('VALKEY_PASSWORD', [''])[0]).strip()

save_db_bandwidth = str(env.get('SAVE_VALKEY_BANDWIDTH', ['True'])[0]).lower().strip() == 'true'
# Variables

bot_name = [name.lower().strip() for name in env.get('BOT_NAME_COMMAND', ['hey'])]

command_chat = str(env.get('CHAT_COMMAND', ['/ask'])[0]).lower().strip()
command_image = str(env.get('IMAGE_COMMAND', ['/img'])[0]).lower().strip()
command_stt = str(env.get('STT_COMMAND', ['/stt'])[0]).lower().strip()
command_tts = str(env.get('TTS_COMMAND', ['/tts'])[0]).lower().strip()
command_transcribe = f'{command_stt}_auto'


exclusive_api_name = str(env.get('EXCLUSIVE_API_NAME', [''])[0])

exclusive_api_chat_ids = env.get('EXCLUSIVE_API_WHITELIST', [])
SUDO_LIST = env.get('SUDO_USER_LIST', [])
donate_url = env.get('VIP_GET', ['https://ko-fi.com/gpthon/tiers'])[0]
donate_contact = env.get('VIP_CONTACT', ['@kolomviano'])[0]

BRAVE_SEARCH_APIKEY = env.get('BRAVE_SEARCH_APIKEY', [None])[0]
blacklist_chat_ids = env.get('BLACKLIST_CHAT_ID', [])
whitelist_chat_ids = env.get('WHITELIST_CHAT_ID', [])

default_chat_model = env.get('DEFAULT_CHAT_MODEL', ['chatgpt-4o-latest'])[0]
default_roleplay_model = env.get('DEFAULT_ROLEPLAY_MODEL', ['gpt-3.5-turbo'])[0]

default_stt_model = env.get('DEFAULT_STT_MODEL', ['whisper-large-v3'])[0]
default_tts_voice = env.get('DEFAULT_TTS_VOICE', ['alloy'])[0]

default_img_model = env.get('DEFAULT_IMAGE_MODEL', ['dall-e-3'])[0]
default_vision_model = env.get('DEFAULT_VISION_MODEL', ['chatgpt-4o-latest'])[0]
vision_max_images_seq = int(env.get('VISION_SEQUENCE_IMAGES', ['16'])[0])
default_embedding_model = env.get('DEFAULT_EMBEDDING_MODEL', ['text-embedding-ada-002'])[0]

api_id = int(env.get('API_ID', [''])[0])

session_name = str(env.get('SESSION_NAME', [''])[0])
error_report_channel_id = int(env.get('ERROR_REPORT_CHANNEL_ID', [0])[0])
error_report_channel_thread = int(env.get('ERROR_REPORT_CHANNEL_THREAD', [0])[0])

api_hash = str(env.get('API_HASH', [''])[0])
bot_token = str(env.get('TELEGRAM_TOKEN', [''])[0])

proxy_raw = env.get('API_TUNNEL', [None])[0]
apisproxy=proxy_raw
#apisproxy = {proxy_raw.split("://")[0] + "://": proxy_raw} if proxy_raw is not None else None
#if apisproxy:
#    apisproxy = next(iter(apisproxy.values()))

logger.info("ETH: 0x69b81AaE4e93bC5432dD2eFF320c4B43721419c9")

basepath = Path(__file__).resolve().parents[1]
logger.debug(f'Base path: {basepath}')

openai_style_apis = {}
roleplay_enabled = False
bot_prompts = {}
API_WAIT_CONFIG = {}
PAID_PLANS = {}

def load_configurations():
    global openai_style_apis, roleplay_enabled, bot_prompts, API_WAIT_CONFIG, PAID_PLANS

    # Cargar archivos de APIs
    apis_dir = basepath / "resources" / "apis"
    apis_files = os.listdir(apis_dir)
    logger.debug(f'Archivos de APIs encontrados: {apis_files}')

    # Limpiar y recargar APIs
    openai_style_apis.clear()
    for fetcher in [f for f in apis_files if f.endswith(".json")]:
        with open(apis_dir / fetcher, "r", encoding="utf-8") as infile:
            openai_style_apis[fetcher] = load(infile)

    # Actualizar estado de roleplay
    roleplay_enabled = "apis_roleplay.json" in openai_style_apis

    # Cargar prompts del bot
    with open(basepath / "resources" / "prompts.json", "r", encoding="utf-8") as infile:
        bot_prompts = load(infile)

    # Cargar configuración de rate limits
    with open(basepath / "resources" / "apis_ratelimits.json", "r", encoding="utf-8") as infile:
        API_WAIT_CONFIG = load(infile)

    # Cargar planes VIP
    with open(basepath / "resources" / "vip_plans.json", "r", encoding="utf-8") as infile:
        PAID_PLANS = load(infile)
    
    return "Configs 🆗"

logger.info(load_configurations())

allowed_chat_mimetypes = ["plain", "javascript"]
allowed_image_mimetypes = ["jpeg", "webp", "webm", "mp4"]


bot = None

bot_data = None
bot_mention = None

async def send_logs_to_channel(text, parse_mode='markdown'):
    try:
        if error_report_channel_id and error_report_channel_thread:
            if len(text) <= 4090:
                await bot.send_message(message=f'```{text}```', entity=error_report_channel_id, reply_to=error_report_channel_thread, link_preview=False, parse_mode=parse_mode)
            else:
                message_parts = [text[i:i+4090] for i in range(0, len(text), 4090)]
                for part in message_parts:
                    for _ in range(0, len(message_parts)):
                        await bot.send_message(message=f'```{part}```', entity=error_report_channel_id, reply_to=error_report_channel_thread, link_preview=False, parse_mode=parse_mode)
        else:
            logger.error(f'send_logs_to_channel: {text}')
    except Exception as e:
        logger.error(f"Error in `send_logs_to_channel`. Probably wrong channel and thread id configured: {str(e)}")

stt_commands = [command_stt, command_transcribe]
