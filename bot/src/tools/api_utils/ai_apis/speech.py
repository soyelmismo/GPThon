from asyncio import CancelledError
from bot.src.logs import logger

from bot.src.tools.api_utils.api_selector import select_api_data, shuffle_apis, update_total_reqs
from bot.src.config import default_tts_voice
from io import BytesIO

response_format = "mp3"

async def request_text_to_speech(thisShit, user_id, command):
    response = None
    try:
        tts_pending = True
        while tts_pending:
            model_apis = await shuffle_apis(user_id, thisShit.tts_voice, command)
            logger.debug(f"apis for transcription {model_apis}")
            for model, api in model_apis.items():
                for api_try in api:
                    try:
                        logger.debug(f"Joining transcription with {api_try}")
                        client = await select_api_data(api_try)
                        try:
                            response = await client.audio.speech.create(
                                input=thisShit.prompt,
                                model=model,
                                voice=thisShit.tts_voice or default_tts_voice,
                                response_format=response_format,
                                speed=1.1,
                                timeout=15
                            )             
                        except CancelledError as e:
                            if "nDDñd" not in str(e):
                                continue
                            else:
                                raise e           
                    
                        logger.debug(response)

                        logger.debug("Received, yielding")
                        await update_total_reqs(command, api_try, model, user_id, 1)
                        audio = BytesIO()
                        audio.name = f'{thisShit.prompt[:10]}...tts.{response_format}'
                        audio.write(response.content)
                        yield audio, "stop"
                    except CancelledError as e:
                        tts_pending = False
                        raise e
                    except Exception as e:
                        await update_total_reqs(command, api_try, model, user_id, 0, response, e)
                        logger.error(f"Error with {api_try}: {str(e)}")
                        continue

            else:
                tts_pending = False
                yield "🗣 😔❌👍", "fail"
    except Exception as e:
        raise ConnectionAbortedError(f"transcribe_audio exception: {str(e)}... {response}")
