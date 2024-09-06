from openai import AsyncOpenAI
from bot.src.config import (openai_style_apis, exclusive_api_chat_ids,
                            exclusive_api_name, max_total_tokens,
                            command_chat, command_image, command_stt)
from bot.src.logs import logger
from bot.src.tools.tg_tools import send_large_message
from asyncio import create_task, gather, wait_for, CancelledError
from random import uniform, shuffle, randint
from tiktoken import get_encoding
import bot.src.constants as c
from httpx import AsyncClient
from io import BytesIO
from PIL.Image import open



total_tokens = 0

total_reqs = {
    command_chat: ["📚", 0],
    command_image: ["🎨", 0],
    command_stt: ["🎤", 0],
}

api_reqs = {}

async def quick_chat_completion(self, model, conversa, custom_params = None):
    try:

        class tempClass():
            def __init__(sc):
                sc.user_id = self.user_id
                sc.conversation = conversa
                sc.chat_model = model
                sc.streaming = False
                sc.seed = None
                sc.max_tokens = 2048
                sc.temperature = 1
                sc.top_p = 1
                sc.frequency_penalty = 0
                sc.presence_penalty = 0
                sc.used_tokens = 0
                sc.randomizer = False

        
        command = c.command_chat

        temp_instance = tempClass()
        if custom_params:
            temp_instance.temperature = custom_params.get("temperature", 1)
        temp_apis = await shuffle_apis(temp_instance.user_id, temp_instance.chat_model, command)
        logger.debug(f"apis for quick_chat_completion {temp_instance.chat_model}: {temp_apis}")
        quick_pending = True
        while quick_pending:
            logger.debug('quick_chat_completion try.')
            for chat_api in temp_apis:
                logger.debug(f'quick_chat_completion {chat_api}')
                try:
                    responseapi = call_api(self=temp_instance, type = command, api = chat_api, model = temp_instance.chat_model)
                    response, status = await wait_for(responseapi.__anext__(), 60)
                    if status == "stop":
                        logger.debug(f"Returning quick_chat_completion `{response}`")
                        return response
                    else:
                        continue

                except CancelledError:
                    quick_pending = False
                    return "Cancelled"
                except:
                    continue

            else:
                break

        return None
    except Exception as e:
        logger.error(f'quick_chat_completion: {str(e)}')
        return None


async def update_total_reqs(type, api, model, user_id):
    total_reqs[type][1] += 1
    logger.info(f"{total_reqs[type][0]} ({total_reqs[type][1]}) - {api}.{model} ✅ {user_id}")


async def call_api(self, type = None, media=None, api = None, model = None):
    response = None
    if not api_reqs.get(api):
        api_reqs[api] = [0, 0]
    api_reqs[api][0] += 1
    try:
        logger.debug("Initializing OpenAI instance")
        client = AsyncOpenAI(
            api_key=openai_style_apis['apis_normal.json'].get(api)[1],
            base_url=openai_style_apis['apis_normal.json'].get(api)[0]
        )

        if type == command_chat:
                logger.debug(f"Joining chat completion with {api}")
                async for response, status in request_chat_completion(self, api, client):
                    if status == "stop":
                        create_task(update_total_reqs(type, api, model, self.user_id))
                    yield response, status

        elif type == command_stt:
                logger.debug(f"Joining transcription with {api}")
                async for response, status in transcribe_audio(api, model, media, client):
                    if status == "done":
                        create_task(update_total_reqs(type, api, model, self.user_id))
                    yield response, status

        elif type == command_image:
                logger.debug(f"Joining image generation with {api}")
                async for response, status in generate_image(api, model, client, img_params=media):
                    if status != "fail":
                        create_task(update_total_reqs(type, api, model, self.user_id))
                    yield response, status
        else:
            raise Exception("no type matched")
    except Exception as e:
        api_reqs[api][1] += 1
        create_task(send_large_message(f'{str(e)}: {response}\n\nTotal/Failed: {api_reqs[api][0]}/{api_reqs[api][1]}'))
        raise ConnectionRefusedError(f'Error in call_api: {str(e)}')

async def request_chat_completion(self, api, client: AsyncOpenAI):
    response = None
    try:
        logger.debug("Set-up chat payload")
        payload = {
            "messages": self.conversation,
            "max_tokens": min(self.max_tokens * 2, max_total_tokens),
            "model": self.chat_model,
            "stream": self.streaming,
            "seed": self.seed,
            "timeout": 10 if self.streaming else 20
        }

        if not self.randomizer:
            logger.debug("Not using randomizer")
            payload["temperature"] = self.temperature
            payload["top_p"] = self.top_p
            payload["frequency_penalty"] = self.frequency_penalty
            payload["presence_penalty"] = self.presence_penalty
        else:
            logger.debug("Using randomizer")
            payload["temperature"] = uniform(0.1, 2.0)
            payload["top_p"] = uniform(0.1, 1.0)
            payload["frequency_penalty"] = uniform(-2.0, 2.0)
            payload["presence_penalty"] = uniform(-2.0, 2.0)

        res_text = ""
        global total_tokens
        logger.debug("Generating response...")
        response = await client.chat.completions.create(**payload)
        logger.debug(f'Response: {response} <---- Response')
        if not self.streaming:
            logger.debug("No streaming...")
            res_text += response.choices[0].message.content
            if not res_text: 
                raise ValueError(f'"{res_text}" inexistent')
            tok = response.usage.total_tokens or 0 
            total_tokens += tok
            self.used_tokens += tok
            yield res_text, "stop"
        else:
            logger.debug("Using streaming...")
            async for chunk in response:
                logger.debug(f'Chunk: {chunk} <---- Chunk')
                res_text += getattr(chunk.choices[0].delta, 'content', "") or ""
                fr = str(chunk.choices[0].finish_reason).lower()
                if fr in ["stop", "length"]:
                    if not res_text:
                        raise ValueError(f'"{res_text}" inexistent')
                    try:
                        tok = chunk.x_groq.get('usage', {}).get('total_tokens', 0)
                    except:
                        try:
                            tok = chunk.usage.total_tokens
                        except:
                            tok = 0

                    total_tokens += tok
                    self.used_tokens += tok
                    logger.debug(f'Yielding entire response: {res_text}')
                    yield res_text, "stop"
                elif fr in ["content_filter"]:
                    raise ValueError("Censored")

                yield res_text, "continue"

    except Exception as e:
        raise ConnectionAbortedError(f"chat completion exception: {api} {str(e)}... {response}")

async def transcribe_audio(api, model, media, client: AsyncOpenAI):
    response = None
    try:

        response = await client.audio.transcriptions.create(
            model=model,
            file=("voice.ogg", media),
            response_format="text",
            temperature = 0.4,
            timeout=60
        )
        logger.debug(response)
        if not isinstance(response, str):
            response = response.text
            if not response:
                yield response, "fail"

        logger.debug("Received, yielding")

        yield response, "done"

    except Exception as e:
        raise ConnectionAbortedError(f"transcribe_audio exception: {api}: {str(e)}... {response}")

async def generate_image(api, model, client: AsyncOpenAI, img_params):
    response = None
    try:
        if img_params["params"].get("style"):
            temp_prompt = img_params["params"]["style"][1]
        else:
            temp_prompt = img_params["prompt"]
        response = await client.images.generate(
            model=model,
            prompt=temp_prompt,
            size=img_params["params"]["ratio"],
            n=img_params["params"]["photos"],
            quality="hd",
            timeout=60
        )
        logger.debug(response)

        if not isinstance(response, str):
            images = response.data
            img_list = []
            for i in images:
                img_list.append(i.url)
            img_list = await download_images(img_list)
            img_prompt = response.data[0].revised_prompt or img_params["prompt"]
        logger.debug(img_list)

        logger.debug("Received, yielding")

        yield img_list, img_prompt

    except Exception as e:
        raise ConnectionAbortedError(f"image generation exception: {api}: {str(e)}... {response}")

enc = get_encoding("cl100k_base")
async def calculate_token_length(conversation):
    total_tokens = 0
    for msg in conversation:
        # Calcular los tokens del contenido del mensaje
        total_tokens += len(enc.encode(msg["content"]))
        # Considerar tokens adicionales para otros campos como "role"
        total_tokens += len(enc.encode(msg["role"]))
    return total_tokens


async def shuffle_apis(user_id, model, type):
    if type == command_chat:
        temp_apis = c.chat_models[model].copy()
    elif type == command_image:
        temp_apis = c.img_models[model].copy()
    elif type == command_stt:
        temp_apis = c.whisper_models[model].copy()

    shuffle(temp_apis)
    if exclusive_api_name in temp_apis:
        temp_apis.remove(exclusive_api_name)
        temp_apis.append(exclusive_api_name) if user_id in exclusive_api_chat_ids else None
    return temp_apis

async def download_image(client, url):
    response = await client.get(url)
    if response.status_code == 200:
        img_data, _ = await compress_image(response.content, black_check=True)
        return img_data
    return None

async def compress_image(img, black_check = None, file_name = None, mime_type = None, quality = 95):
    try:
        img = BytesIO(img)
        img.seek(0)

        image = open(img)

        if black_check:
            image_gray = image.convert('L')

            if await is_black_image(image_gray):
                raise Exception("Black image detected.")

        img_bytes = BytesIO()

        if mime_type not in c.allowed_image_mimetypes:
            mime_type = "jpeg"

        if not black_check and image.width > 800 or image.height > 800:
            image.thumbnail((800, 800))


        image.save(img_bytes, format=mime_type, quality=quality)
        img_bytes.seek(0)

        if not file_name:
            random_id = randint(0, 99999999)
            file_name = f'{random_id}.{mime_type}'
            
            img_bytes.name = file_name
        return img_bytes, file_name
    except Exception as e:
        raise Exception(f'compress_image: {e}')

async def download_images(urls):
    if not urls:
        raise IndexError("No images received")
    images = []
    async with AsyncClient() as client:
        tasks = [download_image(client, url) for url in urls]
        images = await gather(*tasks)
    return [img for img in images if img is not None]

async def is_black_image(image, block_size=1024):
    width, height = image.size
    
    for y in range(0, height, block_size):
        for x in range(0, width, block_size):
            box = (x, y, min(x + block_size, width), min(y + block_size, height))
            block = image.crop(box)
            pixels = block.getdata()
            if any(pixel != 0 for pixel in pixels):
                return False 

    return True 