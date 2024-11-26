from asyncio import CancelledError
from json import loads
from bot.src.logs import logger

from bot.src.tools.api_utils.api_selector import select_api_data, shuffle_apis, update_total_reqs
from bot.src.config import default_stt_model

import bot.src.constants as c


async def request_transcription(thisShit, media, user_id, command):
    response = None
    res_text = None
    try:
        triggered = media[0]
        media = media[1]
        

        models_to_check = c.whisper_models if c.whisper_models else [default_stt_model]
        stt_pending = True
        while stt_pending:
            for model in models_to_check:
                temp_apis = await shuffle_apis(user_id, model, command)
                logger.debug(f"apis for transcription {temp_apis}")
                for api in temp_apis:
                    try:
                        logger.debug(f"Joining transcription with {api}")
                        if triggered:
                            media.seek(0)
                        client = await select_api_data(api)
                        try:
                            response = await client.audio.transcriptions.create(
                                model=model,
                                file=("voice.ogg", media),
                                response_format="text",
                                #temperature = thisShit.temperature,
                                language = thisShit.stt_language,
                                prompt = thisShit.prompt,
                                timeout=60
                            )
                        except CancelledError as e:
                            if "Cancelled by user." not in str(e):
                                continue
                            else:
                                raise e    
                        try:
                            response = loads(response)
                            if isinstance(response, dict):
                                res_text = response["text"]
                        except:
                            pass
                        logger.debug(res_text)
                        if not res_text:
                            yield response, "fail"

                        logger.debug("Received, yielding")
                        await update_total_reqs(command, api, model, user_id, 1)
                        yield res_text, "stop"
                        stt_pending = False

                    except CancelledError:
                        stt_pending = False
                        raise
                    except Exception as e:
                        await update_total_reqs(command, api, model, user_id, 0, response, e)
                        logger.error(f'getting request_transcription {api}: {str(e)}. Continuing with other api...')
                        continue
            else:
                stt_pending = False
    except Exception as e:
        raise ConnectionAbortedError(f"transcribe_audio exception: {str(e)}... {response}")
