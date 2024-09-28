import os
from pathlib import Path
from json import load
from dotenv import load_dotenv

from bot.src.logs import logger



load_dotenv()

# parse environment variables
env = {key: str(os.getenv(key)).split(',') if os.getenv(key) else [] for key in os.environ}

redis_enabled = str(env.get('ENABLE_REDIS', ['True'])[0]).lower().strip() == 'true'

redis_uri = str(env.get('REDIS_URI', ['127.0.0.1:6379'])[0]).strip()
redis_user = str(env.get('REDIS_USER', [''])[0]).strip()
redis_password = str(env.get('REDIS_PASSWORD', [''])[0]).strip()

save_db_bandwidth = str(env.get('SAVE_REDIS_BANDWIDTH', ['True'])[0]).lower().strip() == 'true'
# Variables

bot_name = str(env.get('BOT_NAME_COMMAND', ['hey'])[0]).lower().strip()

command_chat = str(env.get('CHAT_COMMAND', ['/ask'])[0]).lower().strip()
command_image = str(env.get('IMAGE_COMMAND', ['/img'])[0]).lower().strip()
command_stt = str(env.get('STT_COMMAND', ['/stt'])[0]).lower().strip()
command_transcribe = f'{command_stt}_auto'


exclusive_api_name = str(env.get('EXCLUSIVE_API_NAME', [''])[0])

exclusive_api_chat_ids = env.get('EXCLUSIVE_API_WHITELIST', [])
all_models_vip_ids = env.get('EXCLUSIVE_MODELS_WHITELIST', [])
exclusive_models = env.get('EXCLUSIVE_MODELS_LIST', ['o1-preview', 'gpt-4o', 'gpt-4'])
donate_url = env.get('VIP_GET', ['https://ko-fi.com/gpthon'])[0]
donate_contact = env.get('VIP_CONTACT', ['@kolomviano'])[0]

blacklist_chat_ids = env.get('BLACKLIST_CHAT_ID', [])
whitelist_chat_ids = env.get('WHITELIST_CHAT_ID', [])

default_chat_model = env.get('DEFAULT_CHAT_MODEL', ['chatgpt-4o-latest'])[0]
default_roleplay_model = env.get('DEFAULT_ROLEPLAY_MODEL', ['gpt-3.5-turbo'])[0]
max_input_tokens = int(env.get('MAX_INPUT_TOKENS', [4096])[0])
max_total_tokens = int(env.get('MAX_TOTAL_TOKENS', [8000])[0])

default_stt_model = env.get('DEFAULT_STT_MODEL', ['whisper-large-v3'])[0]
default_tts_voice = env.get('DEFAULT_TTS_VOICE', ['alloy'])[0]

default_img_model = env.get('DEFAULT_IMAGE_MODEL', ['dall-e-3'])[0]
default_vision_model = env.get('DEFAULT_VISION_MODEL', ['chatgpt-4o-latest'])[0]
vision_max_images_seq = int(env.get('VISION_SEQUENCE_IMAGES', ['16'])[0])
text_improve_model = env.get('DEFAULT_TEXT_IMPROVE_MODEL', ['gpt-3.5-turbo'])[0]
default_tool_model = env.get('DEFAULT_TOOL_CALL_MODEL', ['gpt-3.5-turbo'])[0]
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


allowed_chat_mimetypes = ["plain", "javascript"]
allowed_image_mimetypes = ["jpeg", "webp", "webm", "mp4"]


bot = None

bot_data = None

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
