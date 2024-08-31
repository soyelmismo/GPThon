from openai import AsyncOpenAI
from bot.src.config import openai_style_apis
from bot.src.logs import logger
from bot.src.tools.api_utils.img_download import download_images
from bot.src.tools import send_large_message
from asyncio import create_task
from random import uniform

total_tokens = 0

async def call_api(self, type: str = "chat", media=None):
    try:
        logger.debug("Initializing OpenAI instance")
        apiok = self.api if type == "chat" else self.whisper_api if type == "stt" else self.img_api if type == "img" else self.api
        client = AsyncOpenAI(
            api_key=openai_style_apis['apis_normal.json'].get(apiok)[1],
            base_url=openai_style_apis['apis_normal.json'].get(apiok)[0]
        )
        match type:
            case "chat":
                logger.debug(f"Joining chat completion with {self.api}")
                async for response, status in request_chat_completion(self, client):
                    if status == "stop":
                        logger.info(f"📚 - {self.api}.{self.model} ✅")
                    yield response, status

            case "stt":
                logger.debug(f"Joining transcription with {self.whisper_api}")
                async for response, status in transcribe_audio(self, media, client):
                    if status == "done":
                        logger.info(f"🎤 - {self.whisper_api}.{self.whisper_model} ✅")
                    yield response, status
            
            case "img":
                logger.debug(f"Joining image generation with {self.img_api}")
                async for response, status in generate_image(self, client, img_prompt=media):
                    if status != "fail":
                        logger.info(f"🎨 - {self.img_api}.{self.img_model} ✅")
                    yield response, status
    except Exception as e:
        create_task(send_large_message(str(e)))
        raise ConnectionRefusedError(e)




async def request_chat_completion(self, client: AsyncOpenAI):
    logger.debug("Set-up chat payload")
    payload = {
        "messages": self.conversation,
        "max_tokens": self.max_tokens,
        "model": self.model,
        "stream": self.streaming,
        "seed": self.seed,
        "timeout": 4 if self.streaming else 15
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
    try:
        global total_tokens
        logger.debug("Generating response...")
        response = await client.chat.completions.create(**payload)
        logger.debug(f'Response: {response} <---- Response')
        if not self.streaming:
            logger.debug("No streaming...")
            res_text += response.choices[0].message.content
            if not res_text: raise ValueError(f'"{res_text}" inexistent')
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
                    if not res_text: raise ValueError(f'"{res_text}" inexistent')
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
        raise ConnectionAbortedError(f"chat completion exception: {self.api} {str(e)}")

async def transcribe_audio(self, media, client: AsyncOpenAI):
    try:
        with open(media, "rb") as f:
            response_data = await client.audio.transcriptions.create(
                model=self.whisper_model,
                file=("a.mp3", f.read()),
                response_format="text",
                timeout=60
            )
            if not isinstance(response_data, str):
                response_data = response_data.text
                if not response_data: raise
            logger.debug(response_data)

            logger.debug("Received, yielding")

            yield response_data, "done"

    except Exception as e:
        raise ConnectionAbortedError(f"transcribe_audio exception: {self.whisper_api}: {str(e)}")

async def generate_image(self, client: AsyncOpenAI, img_prompt):
    try:
        response = await client.images.generate(
            model=self.img_model,
            prompt=img_prompt,
            size="1024x1024",
            n=1 if self.img_model in ["dall-e-3"] else 4,
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
            img_prompt = response.data[0].revised_prompt or img_prompt
            if not img_list: raise
        logger.debug(img_list)

        logger.debug("Received, yielding")

        yield img_list, img_prompt

    except Exception as e:
        raise ConnectionAbortedError(f"image generation exception: {self.img_api}: {str(e)}")


#ratelimited_types = {
#    "chat": {},
#    "img": {},
#    "stt": {}

#}

#async def cooldown_apis(type, api):
#    if not ratelimited_types[type].get(api, {}):
