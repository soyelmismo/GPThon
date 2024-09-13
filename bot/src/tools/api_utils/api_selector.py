from openai import AsyncOpenAI
from bot.src.config import (openai_style_apis, exclusive_api_chat_ids,
                            exclusive_api_name,
                            command_chat, command_image, command_stt,
                            send_logs_to_channel
                            )
from random import shuffle
import bot.src.constants as c
from bot.src.logs import logger
from asyncio import create_task

total_reqs = {
    command_chat: ["📚", 0],
    command_image: ["🎨", 0],
    command_stt: ["🎤", 0],
    "/embed": ["🃏", 0],
    "/tts": ["🗣", 0],
}

api_reqs = {}


async def update_total_reqs(type, api, model, user_id, status, response = None, error = None):
    if not api_reqs.get(api):
        api_reqs[api] = [0, 0]
    if status == 1:
        api_reqs[api][0] += 1
        logger.info(f"{total_reqs[type][0]} ({total_reqs[type][1]}) - {api}.{model} ✅ {user_id}")
    else:
        api_reqs[api][1] += 1
        create_task(send_logs_to_channel(f'Error message: {str(error)}:\n\nResponse: {str(response)}\n\nAPI: {api}\nModel: {model}\nTotal requests/Failed: {api_reqs[api][0]}/{api_reqs[api][1]}'))


async def select_api_data(api):
    client = AsyncOpenAI(
            api_key=openai_style_apis['apis_normal.json'].get(api)[1],
            base_url=openai_style_apis['apis_normal.json'].get(api)[0]
        )
    return client


async def shuffle_apis(user_id, model, type) -> list[str]:
    if c.chat_models or c.img_models or c.whisper_models or c.embed_models:
        if type == command_chat:
            temp_apis = c.chat_models[model].copy()
        elif type == "/embed":
            temp_apis = c.embed_models[model].copy()
        elif type == command_image:
            temp_apis = c.img_models[model].copy()
        elif type == command_stt:
            temp_apis = c.whisper_models[model].copy()
        elif type == "/tts":
            voice = model
            apis_with_voice = {}
            for speech_model in c.speech_models:
                voices = list(c.speech_models[speech_model]["voices"].keys())
                shuffle(voices)
                if voice in voices:
                    if speech_model not in apis_with_voice:
                        apis_with_voice[speech_model] = []
                    apis_with_voice[speech_model].extend(c.speech_models[speech_model]["voices"][voice])
            for model_list in apis_with_voice.keys():
                shuffle(apis_with_voice[model_list])
            temp_apis = apis_with_voice
        if type != "/tts":
            shuffle(temp_apis)
            if exclusive_api_name in temp_apis:
                temp_apis.remove(exclusive_api_name)
                temp_apis.append(exclusive_api_name) if user_id in exclusive_api_chat_ids else None
    else:
        temp_apis = list(openai_style_apis.keys())
    return temp_apis
