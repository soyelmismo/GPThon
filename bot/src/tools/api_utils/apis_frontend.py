from bot.src.config import (command_chat, command_image, command_stt, command_tts)
from bot.src.logs import logger
from asyncio import  wait_for, CancelledError, sleep

from bot.src.tools.api_utils.api_selector import shuffle_apis
from bot.src.tools.api_utils.ai_apis.chatbot import request_chat_completion
from bot.src.tools.api_utils.ai_apis.transcribe import request_transcription
from bot.src.tools.api_utils.ai_apis.speech import request_text_to_speech
from bot.src.tools.api_utils.ai_apis.imagen import generate_image
from bot.src.tools.api_utils.ai_apis.embedding import request_embedding


async def quick_chat_completion(self, user_id, model):
    try:
        temp_apis = await shuffle_apis(self.user_id, model, command_chat)
        logger.debug(f"apis for quick_chat_completion {model}: {temp_apis}")

        try:

            responseapi = call_api(self=self, command = command_chat, user_id=user_id, model = model, quick = True)
            response, status = await wait_for(responseapi.__anext__(), 60) # type: ignore
            if status == "stop":
                logger.debug(f"Returning quick_chat_completion `{response}`")
                return response
            elif status == "cancel":
                return "Cancelled"

        except CancelledError:
            raise e
        except Exception as e:
            logger.error(f"failed quick chat completion. Retrying, {str(e)}")
        return None
    except CancelledError:
        raise e
    except Exception as e:
        logger.error(f'quick_chat_completion: {str(e)}')
        return None




async def call_api(self, command = None, user_id = None, media=None, model = None, quick = None) :
    response = None
    tries = 0
    # trying = True
    status = "continue"
    while status in ["continue", "error", "stall"]:
    # while trying:
        try:
            if tries == 3:
                raise Exception("max retries reached in call_api.")

            logger.debug("Initializing OpenAI instance")

            if command == command_chat:
                async for response, status in request_chat_completion(self, model, user_id, command=command, quick=quick):
                    # if status == "stop":
                    #     trying = False
                    yield response, status

            elif command == command_stt:
                async for response, status in request_transcription(self, media, user_id, command):
                    # if status == "stop":
                    #     trying = False
                    yield response, status

            elif command == command_tts:
                async for response, status in request_text_to_speech(self, user_id, command):
                    # if status == "stop":
                    #     trying = False
                    yield response, status

            elif command == command_image:
                async for response, reso, status in generate_image(self, model, user_id, command):
                    # if status:
                    #     trying = False
                    yield response, reso, status
            elif command == "/embed":
                async for response, status in request_embedding(self, model, user_id, command):
                    # if status == "stop":
                    #     trying = False
                    yield response, status

            else:
                tries = 3
                raise Exception(f"no command matched {command} from {user_id}")
        except CancelledError as e:
            if "nDDñd" not in str(e):
                raise e
            else:
                # trying = False
                if command != command_image:
                    yield "Cancelled", "cancel"
                else:
                    yield "Cancelled", None, "cancel"
                break
        except Exception as e:
            if tries == 3:
                raise ConnectionRefusedError(f'Error in call_api: {str(e)}')
            logger.debug(f"apis_frontend retrying... {user_id}, {command}")
            await sleep(5)
            tries += 1
            continue
        await sleep(0.1)
