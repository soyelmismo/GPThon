import bot.src.tools.api_utils.gpt as gptools
from random import choice
from unicodedata import normalize, category
from asyncio import sleep, wait_for, CancelledError
from telethon.errors.rpcerrorlist import MessageNotModifiedError, MessageEmptyError
from re import sub
from bot.src.logs import logger
from time import time
from datetime import datetime
from bot.src.handlers.commands.tasks import add_task, gen_cancel_button as gcb
from bot.src.handlers.commands import select_instance, get_id
from bot.src.handlers.commands.vision import do_vision
from telethon.types import RequestedPeerUser
from . import bot, remove_command, extract_media, rate_limit_handler, command_chat, allowed_chat_mimetypes, edit_msg


LOADING_CHOICES = ["😎", "😱", "😳", "🗿", "🥵",
                   "🫣", "🤑", "🫨", "🥱", "🙉",
                   "🤖", "🧐", "🤔", "🤫", "🙄"]


max_kilobytes = 24

def check_size(size):
    return int(size) <= max_kilobytes * 1024


@rate_limit_handler(5, 60)
async def ask_gateway(event, user_id, chat_id, command) -> None:
    logger.debug(event)

    if str(event.message.message).lower().startswith("penis"):
        return await event.reply("🤡")
    class_to_call = await select_instance(chat_id, user_id)

    return await class_to_call.request_wrap(event, user_id, command) # type: ignore


async def ask_wrap(self, event, user_id, transcription, command, task_id, file_meta):
    try:
        prompt_list = None
        placeholder_msg = None
        c_button = gcb(command_chat, task_id)
        if command not in ["/retry"]:
            if file_meta["type"] == "image":
                placeholder_msg = await event.reply(f"...{choice(LOADING_CHOICES)}📷", buttons = c_button)
            prompt_list = await extract_prompt(self, event, user_id, command, transcription, placeholder_msg, c_button, file_meta)
            if not prompt_list:
                logger.debug(f"No prompt detected. Retuning None: {prompt_list}")
                return None

        if not placeholder_msg:
            placeholder_msg = await event.reply(f"...{choice(LOADING_CHOICES)}", buttons = c_button)

        task = do_ask(self, prompt_list, event, user_id, command_chat, placeholder_msg, task_id, c_button)
        msg = await add_task(command_chat, user_id, task, task_id)
        if msg == "CantAddMore":
            await edit_msg(event, placeholder_msg, text = "🫸🫨🫷")
        return
    except Exception as e:
        logger.error(f"ask_wrap: {str(e)}")

async def extract_prompt(self, event, user_id, command, transcription, placeholder_msg, buttons, file_meta = {}):
    try:
        if not isinstance(transcription, str):

            prompt = await remove_command(self.conversation, event, command)
            if len(prompt) < 1 and not file_meta.get("file"):
                if self.roleplaying:
                    await event.reply("🔞❓")
                else:
                    await event.reply("❓")
                return None

        else:
            prompt = transcription
        if self.group_mode:
            prompt = f'{await group_mode_data_fetch(self, event)}: {prompt}'
        list_convo = [{"role": "user", "content": prompt}]
        if file_meta["type"] == "image":
            logger.debug(f'{str(event.chat_id)}, {user_id}, {command}')
            #if str(event.chat_id) == user_id or command == "/vision":
            logger.debug("doing vision")
            vision, file_meta = await do_vision(self, event, prompt, placeholder_msg, buttons, file_meta)
            if not vision:
                logger.debug(f"No vision detected. Retuning None: {vision}")
                return None
            if not prompt:
                prompt = str(file_meta.get("name", f'.{file_meta["mime"]}'))
            #else:
            #    print("not vision")
            #    await event.reply("👁️📷❓")
            #    return
            list_convo[0]["content"] = f'{prompt}\n> .{file_meta["mime"]} context:({vision})'
        if check_size(file_meta["size"]) and (file_meta["type"] == "text" or file_meta["mime"] in allowed_chat_mimetypes):
            file_meta = await extract_media(event, file_meta)
            list_convo.append({"role": "user", "content": f'{file_meta["name"]}: [{file_meta["file"]}]'})
        logger.debug(f'Returning prompt: {list_convo}')
        return list_convo
    except Exception as e:
        raise Exception (f"extract_prompt: {str(e)}")

async def tokens_counter(self):
    try:
        type(self.max_tokens)
        convo_token_limit = self.max_tokens
        current_token_length = await gptools.calculate_token_length(self.conversation)

        if current_token_length > convo_token_limit:
            logger.debug("Detected token limit. Deleting old messages.")
            for i, msg in enumerate(self.conversation):
                if msg["role"] in ["user", "assistant"]:
                    del self.conversation[i]
                    current_token_length = await gptools.calculate_token_length(self.conversation)
                    if current_token_length <= convo_token_limit:
                        break

        logger.debug(f"Convo token length: {await gptools.calculate_token_length(self.conversation)}")
    except Exception as e:
        raise Exception(f'tokens_counter: {str(e)}')

async def process_response_chunk(event, response, done_parts, placeholder_msg, status, task_id, c_button):
    try:
        async def editor_msg(message_text, wait_msg, sub_status):
            if sub_status not in ["stop", "length"]:
                await edit_msg(event, wait_msg, text = f'{message_text}...{choice(LOADING_CHOICES)}', buttons=c_button)
            else:
                await edit_msg(event, wait_msg, text = message_text)
    except Exception as e:
        logger.error(f'editor_msg: {str(e)}')

    try:
        if len(response) > 4080:
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
        else:
            await editor_msg(response, placeholder_msg, status)
        return placeholder_msg

    except (MessageNotModifiedError, MessageEmptyError):
        pass
    except Exception as e:
        raise Exception(f"process_response_chunk: {str(e)}")


async def handle_api_response(self, event, responseapi, placeholder_msg, task_id, c_button):
    try:
        done_parts = []
        status = ""
        response = ""
        start_time = time()
        chat_pending = True
        while chat_pending:
            try:
                try:
                    response, status = await wait_for(responseapi.__anext__(), timeout=60)
                except:  # noqa: E722
                    raise
                
                end_time = time()
                time_diff = end_time - start_time
    
                if time_diff < 0.5 and status not in ["stop", "error"]:
                    continue
                elif status in ["stop", "error"]:
                    raise StopAsyncIteration("internal status break")
                else:
                    if len(response) > 1:
                        placeholder_msg = await process_response_chunk(event, response, done_parts, placeholder_msg, status, task_id, c_button)
                    await sleep(0.03)
                    start_time = time()
            except CancelledError:
                await placeholder_msg.delete()
                chat_pending = False
                return
            except StopAsyncIteration:
                if not response:
                    raise Exception("No text")
                placeholder_msg = await process_response_chunk(event, response, done_parts, placeholder_msg, status, task_id, c_button)
                await update_conversation_history(self, response)
                logger.info(f"💰 {gptools.total_tokens} 💰")
                chat_pending = False
            except Exception as e:
                raise ConnectionError(f"Bucle completion: {e}")
        return placeholder_msg
    except Exception as e:
        raise Exception(f"handle_api_response: {str(e)}")

async def update_conversation_history(self, response):
    try:
        if self.memory:
            if "1-800" in response and ("HOPE" in response or "TALK" in response):
                response = "👍💯!"
            self.conversation.append({"role": "assistant", "content": response})

    except Exception as e:
        raise Exception(f"update_conversation_history: {str(e)}")

async def do_ask(self, prompt_list, event, user_id, command, placeholder_msg, task_id, c_button):
    try:
        logger.debug(command)

        await tokens_counter(self)
        logger.debug(self.conversation)
        self.conversation.extend(prompt_list)
        actual_model = str(self.chat_model)
        temp_apis = await gptools.shuffle_apis(self, actual_model, command)
        logger.debug(f"apis for chat {temp_apis}")
        
        for api in temp_apis:
            try:
                logger.debug("Calling api")
                responseapi = gptools.call_api(self, command, media = None, api = api, model = actual_model)
                logger.debug("Continuing api processing")
                placeholder_msg = await handle_api_response(self, event, responseapi, placeholder_msg, task_id, c_button)
                break
    
            except Exception as e:
                logger.error(f"Error with {api}: {str(e)}")
                continue
        else:
            await edit_msg(event, placeholder_msg, text = '✍️ 😔❌👍')
    except Exception as e:
        raise Exception(f"do_ask: {str(e)}")
    finally:
        if not self.memory:
            await self.delete_conversation(event, user_id)

async def gen_random_name(length=6):
    try:
        vowels = 'aeiou'
        consonants = 'bcdfghjklmnpqrstvwxyz'
        
        name = ''
        for i in range(length):
            if i % 2 == 0:
                name += choice(consonants)
            else:
                name += choice(vowels)
            await sleep(0)
    
        return name.capitalize()
    except Exception as e:
        raise Exception(f"gen_random_name: {str(e)}")
        
async def normalize_text(text):
    try:
        return ''.join(
            c for c in normalize('NFKD', text) 
            if category(c) != 'Mn'
        )
    except Exception as e:
        raise Exception(f"normalize_text: {str(e)}")

async def group_mode_data_fetch(self, event):
    try:
        user_id = await get_id(event)
        if user_id not in self.user_ids_index:
            if self.random_names:
                self.user_ids_index[user_id] = await gen_random_name()
            else:
                user_data: RequestedPeerUser = await bot.get_entity(int(user_id)) # type: ignore
                new_name = (user_data.first_name if user_data.first_name
                            else user_data.username if user_data.username
                            else ""
                            )
                new_name = await normalize_text(new_name)
                new_name = str(sub(r'[^a-zA-Z0-9 _\-\.@]', '', new_name)).strip()

                if not new_name:
                    new_name = await gen_random_name()

                self.user_ids_index[user_id] = new_name
        return self.user_ids_index[user_id]
    except Exception as e:
        logger.error(f"group_mode_data_fetch: {str(e)}")
        return await gen_random_name()
