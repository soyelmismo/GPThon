from random import choice
from io import BytesIO
from uuid import uuid4
from datetime import datetime
from json import dumps
from time import time
from asyncio import sleep, wait_for
from re import sub, DOTALL
from telethon.errors.rpcerrorlist import MessageNotModifiedError, MessageEmptyError

import bot.src.tools.api_utils.apis_frontend as gptools
from bot.src.logs import logger
from bot.src.tools.other_tools import get_conversation
from bot.src.handlers.tasks import add_task, gen_cancel_button as gcb
from bot.src.handlers.commands.tts import tts_wrap

from bot.src.tools.tg_tools import send_msg, edit_msg, select_instance
import bot.src.config as conf


LOADING_CHOICES = ["😎", "😱", "😳", "🗿", "🥵",
                   "🫣", "🤑", "🫨", "🥱", "🙉",
                   "🤖", "🧐", "🤔", "🤫", "🙄"]

#@rate_limit_handler(5, 60)
async def ask_gateway(event, user_id, chat_id, command) -> None:
    logger.debug(event)

    if str(event.message.message).lower().startswith("penis"):
        return await event.reply("🤡")
    class_to_call = await select_instance(chat_id, user_id, event)

    return await class_to_call.request_wrap(event, user_id, command)

async def ask_wrap(self, event, user_id, transcription, command, task_id, file_meta):
    if transcription:
        command = conf.command_chat
    try:
        task = do_ask(self, file_meta, event, user_id, command, transcription, task_id)
        msg = await add_task(conf.command_chat, user_id, task, task_id)
        if not msg:
            return
        elif msg == "CantAddMore":
            await send_msg(event, text = "🫸🫨🫷")
        return
    except Exception as e:
        logger.error(f"ask_wrap: {str(e)}")

async def do_ask(self, file_meta, event, user_id, command, transcription, task_id):
    prompt_list = None
    placeholder_msg = None
    temporal_conversation = False
    try:
        c_button = await gcb(conf.command_chat, task_id)
        placeholder_msg, prompt_list, thisShit = await self.extract_prompt(
            event, user_id, command, transcription, c_button, file_meta
            )
        if not prompt_list or not thisShit:
            return None


        if self.conversation and (not prompt_list[-1]["content"] or prompt_list[-1]["content"] == self.conversation[-1]["content"]):
            prompt_list = []

        if not placeholder_msg:
            placeholder_msg = await event.reply(f"...{choice(LOADING_CHOICES)}", buttons = c_button)

        logger.debug(command)

        logger.debug(self.conversation)
        if command != "/retry":
            if not self.memory and not thisShit.memory:
                await self.delete_conversation(event, user_id)

            if thisShit.forget or (self.memory and not thisShit.memory):
                temporal_conversation = True
                if not thisShit.forget:
                    await thisShit.delete_conversation(event, user_id)
                thisShit.conversation.extend(prompt_list)
                await thisShit.tokens_counter(user_id)

        if not temporal_conversation:
            self.conversation.extend(prompt_list)
            await self.tokens_counter(user_id)
            thisShit.conversation = self.conversation

        if command == "/embed":
            model = thisShit.embedding_model
        else:
            model = thisShit.chat_model

        if command in ["/retry", "/vision"]:
            command = conf.command_chat

        logger.debug("Calling api")
        responseapi = gptools.call_api(thisShit, command, user_id, media = None, model = model)
        logger.debug("Continuing api processing")
        placeholder_msg, response, status = await handle_api_response(thisShit, event, responseapi, placeholder_msg, c_button, command)
        if not placeholder_msg and not response and not status:
            return None
        if command == "/embed":
            await placeholder_msg.delete()
        elif self.to_tts and status not in ["error"]:
            await tts_wrap(thisShit, event, user_id, conf.command_tts, task_id, bot_response = response)

        if thisShit.download:
            await send_msg(
                event,
                "✍",
                file = await get_conversation(thisShit, user_id=user_id),
                disable_delete=True,
                force_document=True
                )

        if not temporal_conversation and self.memory:
            self.conversation = thisShit.conversation
        await self.update_session_tokens(response, thisShit.used_tokens)

    except Exception as e:
        raise Exception(f"do_ask: {str(e)}")



async def process_response_chunk(event, response, done_parts, placeholder_msg, status, c_button):

    async def editor_msg(message_text, wait_msg, sub_status):
        try:
            message_text = sub(
                r'<think>(.*?)</think>',
                lambda match: f'%%\n<think>{match.group(1)}</think>%%' if match.group(1).strip() else '',
                message_text,
                flags=DOTALL
                ).strip()
            if sub_status in ["stop", "length", "error"]:
                await edit_msg(event, wait_msg, text = message_text)
            else:
                await edit_msg(
                    event, wait_msg,
                    text = f'{message_text}...{choice(LOADING_CHOICES)}',
                    buttons=c_button
                )

        except Exception as e:
            logger.error(f'editor_msg: {str(e)}')

    try:
        if len(response) <= 4080:
            await editor_msg(response, placeholder_msg, status)
        else:
            chunks = [response[i:i+4080] for i in range(0, len(response), 4080)]
            for i, chink in enumerate(chunks):
                if i not in done_parts:
                    if status not in ["stop", "length"] and len(chink) < 4080:
                        await editor_msg(chink, placeholder_msg, status)
                    elif status in ["stop", "length"] or len(chink) >= 4080:
                        if i not in done_parts:
                            await editor_msg(chink, placeholder_msg, "stop")
                            done_parts.append(i)
                        if len(done_parts) < len(chunks):
                            placeholder_msg = await event.reply(f"...{choice(LOADING_CHOICES)}")

        return placeholder_msg

    except (MessageNotModifiedError, MessageEmptyError):
        pass
    except Exception as e:
        raise Exception(f"process_response_chunk: {str(e)}") from e

async def handle_api_response(
    self, event, responseapi, placeholder_msg,
    c_button, command = None
    ):
    try:
        done_parts = []
        status = ""
        response = ""
        start_time = time()
        chat_pending = True
        old_response = ""
        while chat_pending:
            try:
                response, status = await wait_for(
                    responseapi.__anext__(),
                    timeout=60
                )

                if status == "cancel":
                    await placeholder_msg.delete()
                    chat_pending = False
                    return None, None, None

                end_time = time()
                time_diff = end_time - start_time

                if time_diff < 0.5 and status not in ["stop"]:
                    continue
                elif status in ["stop"]:
                    raise StopAsyncIteration("internal status break")
                else:
                    if len(response) > 1 and old_response != response:
                        placeholder_msg = await process_response_chunk(event, response, done_parts, placeholder_msg, status, c_button)
                        old_response = str(response)
                    await sleep(0.03)
                    start_time = time()                
            except StopAsyncIteration as e:

                if not response:
                    raise StopAsyncIteration("No text") from e
                if command == "/embed":
                    await process_embeddings_file(self, event, response)
                else:
                    if self.debug:
                        response = f'{response}\n\n```\nmodel: {self.chat_model}\n```'
                    placeholder_msg = await process_response_chunk(
                        event, response, done_parts,
                        placeholder_msg, status, c_button
                    )
                    if status not in ["error"]:
                        if response.startswith("<think>") and "</think>" in response:
                            response = sub(r'<think>.*?</think>', '', response, flags=DOTALL).strip()
                            response = response.strip()
                        self.conversation.append({"role": "assistant", "content": response})
                chat_pending = False
            except Exception as e:
                raise ConnectionError(f"Bucle completion: {e}") from e
        return placeholder_msg, response, status
    except Exception as e:
        await edit_msg(event, placeholder_msg, '✍️ 😔❌👍')
        raise Exception(f"handle_api_response: {str(e)}") from e

async def process_embeddings_file(self, event, response):
    try:
        embed_file = BytesIO()
        embed_file.name = '🃏.json'
        last_msg = self.conversation[-1]["content"]
        embed_data = {
            "id": uuid4().hex,
            "text": last_msg,
            "context": {"user": self.user_id, "category": "chat"},
            #"relevance": {"frequency": frequency, "importance": importance},
            "created_at": datetime.now().isoformat(),
            "vector": response
        }
        embed_file.write(dumps(embed_data, indent=4, ensure_ascii=False).encode('utf-8'))  
        await send_msg(event, "👍", embed_file, force_document=True, disable_delete=True)
        return
    except Exception as e:
        raise Exception(f"process_embeddings_file: {str(e)}") from e
