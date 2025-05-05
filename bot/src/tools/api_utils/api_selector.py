from openai import AsyncOpenAI
from asyncio import sleep
from re import search
from random import shuffle
from datetime import datetime, timedelta
from bot.src.logs import logger
import bot.src.config as conf
import bot.src.constants as c

total_reqs = {
    conf.command_chat: ["📚", 0],
    conf.command_image: ["🎨", 0],
    conf.command_stt: ["🎤", 0],
    "/embed": ["🃏", 0],
    conf.command_tts: ["🗣", 0],
}

api_reqs: dict[dict[dict[int, int]]] = {}

rate_limited: dict[tuple[str, str], dict] = {}

async def api_rate_limiter_task(interval: int = 60):  # tiempo en segundos
    logger.info("Started APIs rate limit check")
    while True:
        await sleep(interval)
        now = datetime.now()
        for key in list(rate_limited.keys()):
            data = rate_limited[key]
            if (now - data['timestamp']).total_seconds() >= data['duration']:
                rate_limited.pop(key, None)
                logger.info(f'{c.colors["green"]}API {key[1]} for model {key[0]} removed from rate limit list.{c.colors["r"]}')


async def wait_tomorrow(today, future_hour):
    planned_date = today.replace(hour=future_hour, minute=5, second=0, microsecond=0)
    if today.hour >= future_hour:
        planned_date += timedelta(days=1)
    wait_time = planned_date - datetime.now()
    return wait_time.total_seconds()

async def check_api_rate_limit(api: str, model: str, error: str) -> None:
    today = datetime.now()
    future_seconds = (
            conf.API_WAIT_CONFIG[api].get("wait_seconds")
            or await wait_tomorrow(today, conf.API_WAIT_CONFIG[api]["wait_time"])
        ) if (conf.API_WAIT_CONFIG[api].get("maintenance_condition", "") in error
              or conf.API_WAIT_CONFIG[api].get("error_condition", "") in error) else None

    if future_seconds:

        rate_limited[(model, api)] = {
        'timestamp': today,
        'duration': future_seconds
        }

        logger.info(f'{c.colors["red"]}API {api} for {model} rate limited for {future_seconds} seconds.{c.colors["r"]}')

async def update_total_reqs(type, api, model, user_id, status, response = None, error = None):
    if model not in api_reqs:
        api_reqs[model] = {}
    if api not in api_reqs[model]:
        api_reqs[model][api] = [0, 0] #Success / Failed

    if status == 1:
        api_reqs[model][api][0] += 1
        total_reqs[type][1] += 1
        icon_emoji = "✅"
        sc = "green"
    else:
        icon_emoji = "❌"
        sc = "red"
        error = str(error)
        if "!DOCTYPE html" in error:
            error = search(r'<title>(.*?)<\/title>', error)
            error = error.group(1)
        if (model, api) not in rate_limited and api in conf.API_WAIT_CONFIG:
            await check_api_rate_limit(api, model, error)
        api_reqs[model][api][1] += 1

        await conf.send_logs_to_channel((
            f"Error message: {error}\n\n"
            f"Response: {str(response)}\n\n"
            f"API: {api}\n"
            f"Model: {model}\n"
            f"Success/Failed: {api_reqs[model][api][0]}/{api_reqs[model][api][1]}\n\n"
            f"Triggered by: {user_id}"
        ))

    logger.info(
        f"{c.colors[sc]}{total_reqs[type][0]} ({total_reqs[type][1]}) - {api}.{model} {icon_emoji} {user_id}{c.colors["r"]}"
    )

async def select_api_data(api):
    client = AsyncOpenAI(
            api_key=conf.openai_style_apis['apis_normal.json'].get(api)[1],
            base_url=conf.openai_style_apis['apis_normal.json'].get(api)[0]
        )
    return client


async def shuffle_apis(user_id, model, type) -> list[str]:
    if c.chat_models or c.img_models or c.whisper_models or c.embed_models:
        if type == conf.command_chat:
            temp_apis = c.chat_models[model].copy()
        elif type == "/embed":
            temp_apis = c.embed_models[model].copy()
        elif type == conf.command_image:
            temp_apis = c.img_models[model].copy()
        elif type == conf.command_stt:
            temp_apis = c.whisper_models[model].copy()
        elif type == conf.command_tts:
            apis_with_voice = {}
            for speech_model, model_data in c.speech_models.items():
                if model in model_data["voices"]:
                    if speech_model not in apis_with_voice:
                        apis_with_voice[speech_model] = []
                    apis_with_voice[speech_model].extend(model_data["voices"][model])
            for _, apis in apis_with_voice.items():
                shuffle(apis)
                await move_exclusive_api(user_id, apis)
            temp_apis = apis_with_voice
        if type != conf.command_tts:
            shuffle(temp_apis)
            await move_exclusive_api(user_id, temp_apis)
    else:
        temp_apis = list(conf.openai_style_apis)


    to_remove = [api for api in temp_apis if (model, api) in rate_limited]
    for api in to_remove:
        temp_apis.remove(api)
        logger.warning(f"{c.colors["yellow"]}{api} API is rate-limited for {model}, removing from list.{c.colors["r"]}")

    return temp_apis

async def move_exclusive_api(user_id, api_list):
    if conf.exclusive_api_name in api_list:
        api_list.remove(conf.exclusive_api_name)
        if user_id in conf.exclusive_api_chat_ids:
            api_list.append(conf.exclusive_api_name)
    return api_list