from openai import OpenAI
from bot.src.config import openai_style_apis
from bot.src.logs import logger
from random import uniform

total_tokens = 0

async def call_api(self, type: str = "chat", media=None):
    logger.debug("Initializing OpenAI instance")
    apiok = self.api if type == "chat" else self.whisper_api if type == "stt" else self.img_api if type == "img" else self.api
    client = OpenAI(
        api_key=openai_style_apis['apis_normal.json'].get(apiok)[1],
        base_url=openai_style_apis['apis_normal.json'].get(apiok)[0]
    )
    match type:
        case "chat":
            logger.debug("Joining chat completion")
            async for response, status in request_chat_completion(self, client):
                if status == "stop":
                    logger.info(f"📚 - {self.api}.{self.model} ✅")
                yield response, status

        case "stt":
            logger.debug("Joining transcription")
            async for response, status in transcribe_audio(self, media, client):
                if status == "done":
                    logger.info(f"🎤 - {self.whisper_api}.{self.whisper_model} ✅")
                yield response, status
        
        case "img":
            logger.debug("Joining image generation")
            async for response, status in generate_image(self, client, img_prompt=media):
                if status != "fail":
                    logger.info(f"🎨 - {self.img_api}.{self.img_model} ✅")
                yield response, status

async def request_chat_completion(self, client: OpenAI):
    logger.debug("Set-up chat payload")
    payload = {
        "messages": self.conversation,
        "max_tokens": abs(int(self.max_tokens)),
        "model": self.model,
        "stream": self.streaming,
        "seed": self.seed,
        "timeout": 3 if self.streaming else 7
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
        response = client.chat.completions.create(**payload)
        logger.debug(f'Response: {response} <---- Response')
        if not self.streaming:
            logger.debug("No streaming...")
            res_text += response.choices[0].message.content
            total_tokens += response.usage.total_tokens
            yield res_text, "stop"
        else:
            logger.debug("Using streaming...")
            for chunk in response:
                logger.debug(f'Chunk: {chunk} <---- Chunk')
                res_text += getattr(chunk.choices[0].delta, 'content', "") or ""
                if chunk.choices[0].finish_reason == "stop":
                    #print(chunk.usage)
                    total_tokens += chunk.usage.total_tokens if chunk.usage else chunk.x_groq.get('usage', {}).get('total_tokens', 0)
                    logger.debug(f'Yielding entire response: {res_text}')
                    yield res_text, "stop"

                yield res_text, "continue"

    except Exception as e:
        logger.debug(f"request_chat_completion exception: {str(e)}")
        if not res_text:
            raise ConnectionError(f"Session error, {str(e)}")
        raise ConnectionError(f"Not possible, {str(e)}")

async def transcribe_audio(self, media, client: OpenAI):
    try:
        with open(media, "rb") as f:
            response_data = client.audio.transcriptions.create(
                model=self.whisper_model,
                file=("a.mp3", f.read()),
                response_format="text"
            )
            if not isinstance(response_data, str):
                response_data = response_data.text
                if not response_data: raise
            logger.debug(response_data)

            logger.debug("Received, yielding")
            
            yield response_data, "done"

    except Exception as e:
        logger.debug(f"transcribe_audio exception: {self.whisper_api}: {str(e)}")
        yield "fail", "fail"

async def generate_image(self, client: OpenAI, img_prompt):
    try:
        response = client.images.generate(
            model=self.img_model,
            prompt=img_prompt,
            size="1024x1024",
            quality="hd"
        )
        logger.debug(response)

        if not isinstance(response, str):
            url = response.data[0].url
            img_prompt = response.data[0].revised_prompt or img_prompt
            if not url: raise
        logger.debug(url)

        logger.debug("Received, yielding")

        yield url, img_prompt

    except Exception as e:
        logger.debug(f"image generation exception: {self.img_api}: {str(e)}")
        yield "fail", "fail"
