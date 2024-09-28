from openai import AsyncOpenAI
from asyncio import sleep

import bot.src.config as conf
from random import shuffle
import bot.src.constants as c
from bot.src.logs import logger
from datetime import datetime, timedelta

total_reqs = {
    conf.command_chat: ["📚", 0],
    conf.command_image: ["🎨", 0],
    conf.command_stt: ["🎤", 0],
    "/embed": ["🃏", 0],
    "/tts": ["🗣", 0],
}

api_reqs = {}

rate_limited = set()

async def set_temp_rate(api, duration):
    rate_limited.add(api)
    await sleep(duration)
    rate_limited.discard(api)

async def wait_tomorrow(future_hour):
    today = datetime.now()
    planned_date = today.replace(hour=future_hour, minute=0, second=0, microsecond=0)
    if today.hour >= future_hour:
        planned_date += timedelta(days=1)
    wait_time = planned_date - datetime.now()
    return wait_time.total_seconds()

async def check_api_rate_limit(api, error):
    future_seconds = None
    if api == "fresed" and "5 minutes" in error:
        future_seconds = 300
    elif api == "electron" and "Insufficient balance" in error:
        future_seconds = await wait_tomorrow(16)
    if future_seconds:
        conf.bot._loop.create_task(set_temp_rate(api, future_seconds))

async def update_total_reqs(type, api, model, user_id, status, response = None, error = None):
    if api not in api_reqs:
        api_reqs[api] = [0, 0]

    if status == 1:
        api_reqs[api][0] += 1
        total_reqs[type][1] += 1
        icon_emoji = "✅"
    else:
        icon_emoji = "❌"
        error = str(error)
        await check_api_rate_limit(api, error)
        api_reqs[api][1] += 1
        conf.bot._loop.create_task(conf.send_logs_to_channel(f'Error message: {error}:\n\nResponse: {str(response)}\n\nAPI: {api}\nModel: {model}\nSuccess/Failed: {api_reqs[api][0]}/{api_reqs[api][1]}\n\nTriggered by: {user_id}'))
    logger.info(f"{total_reqs[type][0]} ({total_reqs[type][1]}) - {api}.{model} {icon_emoji} {user_id}")

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
        elif type == "/tts":
            voice = model
            apis_with_voice = {}
            for speech_model, voices in c.speech_models.items():
                if voice in voices:
                    if speech_model not in apis_with_voice:
                        apis_with_voice[speech_model] = []
                    apis_with_voice[speech_model].extend(voices[voice])
            for _, apis in apis_with_voice:
                shuffle(apis)
            temp_apis = apis_with_voice
        if type != "/tts":
            shuffle(temp_apis)
            if conf.exclusive_api_name in temp_apis:
                temp_apis.remove(conf.exclusive_api_name)
                if user_id in conf.exclusive_api_chat_ids:
                    temp_apis.append(conf.exclusive_api_name)
    else:
        temp_apis = list(conf.openai_style_apis)

    for api in rate_limited:
        if api in temp_apis:
            logger.warning(f"{api} API is rate-limited, removing from list.")
            temp_apis.remove(api)

    return temp_apis
