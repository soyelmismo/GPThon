from bot.src.config import (command_chat, command_image, command_stt)
from bot.src.logs import logger
from asyncio import  wait_for, CancelledError

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
        self.streaming = False

        try:
            self.tool_call = False
            responseapi = call_api(self=self, command = command_chat, user_id=user_id, model = model)
            response, status = await wait_for(responseapi.__anext__(), 60) # type: ignore
            if status == "stop":
                logger.debug(f"Returning quick_chat_completion `{response}`")
                return response

        except CancelledError:
            return "Cancelled"
        except Exception as e:
            logger.error(f"failed quick chat completion. Retrying, {str(e)}")
        return None
    except Exception as e:
        logger.error(f'quick_chat_completion: {str(e)}')
        return None




async def call_api(self, command = None, user_id = None, media=None, model = None) :
    response = None
    try:
        logger.debug("Initializing OpenAI instance")
        
        if command == command_chat:
            async for response, status in request_chat_completion(self, model, user_id, command=command):
                yield response, status

        elif command == command_stt:
            async for response, status in request_transcription(self, media, user_id, command):
                yield response, status

        elif command == "/tts":
            async for response, status in request_text_to_speech(self, user_id, command):
                yield response, status

        elif command == command_image:
            async for response, status in generate_image(self, model, user_id, command):
                yield response, status
        elif command == "/embed":
            async for response, status in request_embedding(self, model, user_id, command):
                yield response, status

        else:
            raise Exception("no command matched")
    except CancelledError as e:
        raise e
    except Exception as e:
        raise ConnectionRefusedError(f'Error in call_api: {str(e)}')
