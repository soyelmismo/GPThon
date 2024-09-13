import bot.src.tools.api_utils.apis_frontend as gptools
from random import choice
from io import BytesIO
from unicodedata import normalize, category
from asyncio import sleep, wait_for, CancelledError
from telethon.errors.rpcerrorlist import MessageNotModifiedError, MessageEmptyError
from re import sub
from bot.src.logs import logger
from time import time
from bot.src.handlers.commands.tasks import add_task, gen_cancel_button as gcb
from bot.src.handlers.commands import select_instance, get_id
from bot.src.handlers.commands.vision import do_vision
from bot.src.handlers.commands.tts import tts_wrap
from telethon.types import RequestedPeerUser
from . import bot, remove_command, extract_media, rate_limit_handler, command_chat, allowed_chat_mimetypes, edit_msg
from bot.src.tools.tg_tools import send_msg
from bot.src.tools.api_utils.ai_apis import shared_vars as svars
from bot.src.tools.api_utils.call_tools.backends.website_view import urls_wrapper

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
    if transcription:
        command = command_chat
    thisShit = None
    try:
        prompt_list = None
        placeholder_msg = None
        c_button = await gcb(command_chat, task_id)
        placeholder_msg, prompt_list, thisShit = await extract_prompt(self, event, user_id, command, transcription, c_button, file_meta)
        if not prompt_list or not thisShit:
            return None

        if not placeholder_msg:
            placeholder_msg = await event.reply(f"...{choice(LOADING_CHOICES)}", buttons = c_button)

        task = do_ask(self, thisShit, prompt_list, event, user_id, command, placeholder_msg, task_id, c_button)
        msg = await add_task(command_chat, user_id, task, task_id)
        if msg == "CantAddMore":
            await edit_msg(event, placeholder_msg, text = "🫸🫨🫷")
        return
    except Exception as e:
        logger.error(f"ask_wrap: {str(e)}")


async def extract_prompt(self, event, user_id, command, transcription, buttons, file_meta = {}):
    placeholder_msg = None
    try:
        if not isinstance(transcription, str):
            c_back = str(command)
            prompt = await remove_command(self.conversation, event, command)

            if len(prompt) < 2 and not file_meta.get("type") and command not in ["/retry"]:
                if self.roleplaying:
                    await event.reply("🔞❓")
                else:
                    await event.reply("❓")
                return None, None, None

            
            if file_meta["type"] == "image":
                command = "/vision"
            
            command = c_back

        else:
            prompt = transcription
            file_meta["type"] = "transcription"
        from bot.src.tools.params.inference_params import extract_arguments
        thisShit = await extract_arguments(self, event, prompt, command, user_id, file_meta=file_meta)
        if not thisShit:
            return None, None, None
        if self.group_mode:
            prompt = f'{await group_mode_data_fetch(self, event)}: {prompt}'
        list_convo = []
        if self.tool_call:
            
            urls_dicts = await urls_wrapper(prompt)
            if urls_dicts:
                list_convo.extend(urls_dicts)
        list_convo.append({"role": "user", "content": prompt})
        if file_meta["type"] == "image":
            logger.debug(f'{str(event.chat_id)}, {user_id}, {command}')
            #if str(event.chat_id) == user_id or command == "/vision":
            logger.debug("doing vision")
            tk_bak = int(thisShit.max_tokens)
            placeholder_msg = await event.reply(f"...{choice(LOADING_CHOICES)}📷", buttons = buttons)
            vision, file_meta = await do_vision(thisShit, event, user_id, prompt, placeholder_msg, buttons, file_meta)
            thisShit.max_tokens = tk_bak
            if not vision:
                logger.debug(f"No vision detected. Retuning None: {vision}")
                return None, None, None
            if not prompt:
                prompt = str(file_meta.get("name", f'.{file_meta["mime"]}'))
            list_convo[0]["content"] = f'{prompt}\n> .{file_meta["mime"]} context:({vision})'
        if check_size(file_meta["size"]) and (file_meta["type"] == "text" or file_meta["mime"] in allowed_chat_mimetypes):
            file_meta = await extract_media(event, file_meta)
            list_convo.append({"role": "user", "content": f'{file_meta["name"]}: [{file_meta["file"]}]'})
        logger.debug(f'Returning prompt: {list_convo}')
        return placeholder_msg, list_convo, thisShit
    except Exception as e:
        raise Exception (f"extract_prompt: {str(e)}")

async def handle_summarize(self, user_id, conversation_text = None):
    try:
        logger.info("Trying to summarize the conversation.")
        from bot.src.tools.params.mini_tools import get_conversation
        tempbak = float(self.temperature)
        latest_msgs = []
        if len(self.conversation) > 5:
            latest_msgs = self.conversation[-5:]
        latest_msgs.append(self.conversation[-1:][0])
        conversation_text = await get_conversation(self, user_id=user_id, summary=True)
        await self.delete_conversation(summarized = 1)
        self.temperature = tempbak
        self.conversation.append({"role": "system", "content": f'context:\n\n{conversation_text}'})
        self.conversation.extend(latest_msgs)
        return conversation_text
    except Exception as e:
        raise Exception(f'handle_summarize: {str(e)}')



from tiktoken import get_encoding
enc = get_encoding("cl100k_base")
async def calculate_token_length(conversation):
    total_tokens = 0
    for msg in conversation:
        # Calcular los tokens del contenido del mensaje
        total_tokens += len(enc.encode(msg["content"]))
        # Considerar tokens adicionales para otros campos como "role"
        total_tokens += len(enc.encode(msg["role"]))
    return total_tokens



async def tokens_counter(self, user_id):
    try:
        current_token_length = await calculate_token_length(self.conversation)
        conversation_text = None
        if current_token_length > int(self.max_tokens):
            logger.info("Detected token limit.")
            if self.summarize and not self.roleplaying:
                conversation_text = await handle_summarize(self, user_id)
            if not conversation_text:
                logger.info("Deleting old messages.")
                for i, msg in enumerate(self.conversation):
                    if msg["role"] in ["user", "assistant"]:
                        del self.conversation[i]
                        current_token_length = await calculate_token_length(self.conversation)
                        if current_token_length <= self.max_tokens:
                            break

        logger.info(f"Convo token length: {await calculate_token_length(self.conversation)}")

    except Exception as e:
        raise Exception(f'tokens_counter: {str(e)}')


async def process_response_chunk(event, response, done_parts, placeholder_msg, status, c_button):
    try:
        async def editor_msg(message_text, wait_msg, sub_status):
            if sub_status not in ["stop", "length", "error"]:
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


async def handle_api_response(self, event, responseapi, placeholder_msg, task_id, c_button, command = None):
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
                        placeholder_msg = await process_response_chunk(event, response, done_parts, placeholder_msg, status, c_button)
                    await sleep(0.03)
                    start_time = time()
            except CancelledError:
                await placeholder_msg.delete()
                chat_pending = False
                return
            except StopAsyncIteration:
                    
                if not response:
                    raise Exception("No text")
                if command == "/embed":
                    await process_embeddings_file(self, event, response)
                else:
                    placeholder_msg = await process_response_chunk(event, response, done_parts, placeholder_msg, status, c_button)
                    if status not in ["error"]:
                        await update_conversation_history(self, response)
                chat_pending = False
            except Exception as e:
                raise ConnectionError(f"Bucle completion: {e}")
        return placeholder_msg, response, status
    except Exception as e:
        await edit_msg(event, placeholder_msg, '✍️ 😔❌👍')
        raise Exception(f"handle_api_response: {str(e)}")

async def process_embeddings_file(self, event, response):
    try:
        embed_file = BytesIO()
        embed_file.name = '🃏.json'
        from uuid import uuid4
        from datetime import datetime
        from json import dumps
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
        raise Exception(f"process_embeddings_file: {str(e)}")

async def update_conversation_history(self, response):
    try:
        if self.memory:
            if "1-800" in response and ("HOPE" in response or "TALK" in response):
                response = "👍💯!"
            self.conversation.append({"role": "assistant", "content": response})

    except Exception as e:
        raise Exception(f"update_conversation_history: {str(e)}")

async def do_ask(self, thisShit, prompt_list, event, user_id, command, placeholder_msg, task_id, c_button):
    
    try:
        logger.debug(command)

        
        logger.debug(self.conversation)
        self.conversation.extend(prompt_list)
        await tokens_counter(self, user_id)
        thisShit.conversation = self.conversation


        if command == "/embed":
            model = thisShit.embedding_model
        else:
            model = thisShit.chat_model

        if command == "/retry":
            command = command_chat

        logger.debug("Calling api")
        responseapi = gptools.call_api(thisShit, command, user_id, media = None, model = model)
        logger.debug("Continuing api processing")
        placeholder_msg, response, status = await handle_api_response(self, event, responseapi, placeholder_msg, task_id, c_button, command)
        if command == "/embed":
            await placeholder_msg.delete()
        elif self.to_tts and status not in ["error"]:
            await tts_wrap(thisShit, event, user_id, "/tts", task_id, bot_response = response)

    except Exception as e:
        raise Exception(f"do_ask: {str(e)}")
    finally:
        self.conversation = thisShit.conversation
        self.used_tokens += thisShit.used_tokens or 0
        svars.total_tokens += thisShit.used_tokens or 0
        self.session_tokens = (await calculate_token_length(self.conversation))
        logger.info(f"💰 {svars.total_tokens} 💰")
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
