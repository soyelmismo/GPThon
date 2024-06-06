from bot.src.config import openai_style_apis
beauty_list = {"False": list(openai_style_apis['apis_normal.json'].keys()), "True": list(openai_style_apis["apis_roleplay.json"].keys()), "Whisper": [key for key, value in openai_style_apis['apis_normal.json'].items() if len(value) == 3]}

from json import loads
from bot.src.logs import logger

async def call_api(self, session, type: str = "chat", media_bytes = None):

    headers = {
        "Authorization": f"Bearer {openai_style_apis['apis_normal.json'].get(self.api)[1] if not self.roleplaying else openai_style_apis['apis_roleplay.json'].get(self.api)[1]}"
    }

    api_endpoint = openai_style_apis["apis_normal.json"].get(self.api)[0] if not self.roleplaying else openai_style_apis["apis_roleplay.json"].get(self.api)[0]
    if type == "chat":
        async for response, status in request_chat_completion(self, session, headers, f'{api_endpoint}/chat/completions'):
            yield response, status

    elif type == "stt":
        async for response, status in transcribe_audio(session, headers, endpoint = [f'{openai_style_apis["apis_normal.json"][self.api][0]}/audio/transcriptions', openai_style_apis["apis_normal.json"][self.api][2]], mp3_bytes = media_bytes):
            yield response, status

async def request_chat_completion(self, session, headers, endpoint):
    payload = {
        "messages": self.conversation,
        "temperature": 0.1,
        "top_p": 0.99,
        "frequency_penalty": 1.0,
        "presence_penalty": 1.0,
        #"temperature": uniform(0.1, 2.0),
        #"top_p": uniform(0.1, 1.0),
        #"frequency_penalty": uniform(-2.0, 2.0),
        #"presence_penalty": uniform(-2.0, 2.0),
        "max_tokens": 2048,
        "model": self.model,
        "stream": self.streaming
    }
    res_text = ""
    async with session:
        try:

            async with session.post(
                endpoint,
                headers=headers,
                json=payload,
                raise_for_status=False,
                ssl=True
            ) as response:

                if response.status != 200:
                    raise ConnectionError(f"Session response error: {response.text}")
                logger.debug(f"{self.api}: code {response.status}")
                async for chunk in response.content.iter_any():
                    try:
                        chunk = chunk.decode("utf-8")

                        if payload.get("stream") == False:
                            chunk = loads(chunk)
                            res_text += chunk.get("choices", [])[0].get("message", {}).get("content", "") 
                            if len(res_text) > 0:
                                yield res_text, "stop"
                                break
                        else:
                            matches = chunk.split('data: ')[1:]
                            for match in matches:
                                if match.startswith("["): continue
                                chunk = loads(match)
                                stop = chunk["choices"][0].get("finish_reason", None)
                                res_text += chunk["choices"][0]["delta"].get("content", "")

                                if response.content.at_eof() or isinstance(stop, str):
                                    yield res_text, "stop"
                                    break
                                else:
                                    yield res_text, "continue"
                    except Exception as e:
                        print("Inside iteration:", e)
                        continue
                yield res_text, "stop"
                return
        except Exception as e:
            print("excepcion", e)
            if len(res_text) < 1:
                raise ConnectionError(f"Session error, {e}")
            raise ConnectionError(f"Not possible, {e}")
            #yield f"Error... {e}", "error"
        finally:
            if not session.closed:
                await session.close()

from aiohttp import FormData
async def transcribe_audio(session, headers, endpoint, mp3_bytes):

    data = FormData()
    data.add_field("file", mp3_bytes, content_type="audio/mp3")
    data.add_field("model", endpoint[1])

    async with session:
        async with session.post(endpoint[0], headers=headers, data=data) as response:
            if response.status != 200:
                    raise ConnectionError(f"Session response error: {response.text}")
            response_data = await response.json()
            if response_data.get("text"):
                logger.debug("Received, yielding")
                yield response_data["text"], "done"
            else:
                yield "fail", "fail"
