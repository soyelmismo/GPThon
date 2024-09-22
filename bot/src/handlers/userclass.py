
from json import loads, JSONDecodeError
from asyncio import sleep
from datetime import datetime
from uuid import uuid4
from re import sub
from random import choice
from unicodedata import normalize, category

from telethon.types import RequestedPeerUser

from bot.src.tools.api_utils.ai_apis import shared_vars as svars
from bot.src.tools.other_tools import get_conversation, calculate_token_length
from bot.src.tools.tg_tools import check_media_type, extract_media, remove_command, get_id
from bot.src.tools.params.inference_params import extract_arguments

import bot.src.config as conf
from bot.src.handlers.commands.vision import do_vision
from bot.src.tools.api_utils.call_tools.backends.website_view import urls_wrapper

from bot.src import constants as co
from bot.src.handlers.commands.stt import stt_wrap

from bot.src.handlers.commands.img import img_wrap
from bot.src.handlers.commands.tts import tts_wrap
from bot.src.handlers.commands.ask import ask_wrap, LOADING_CHOICES
from bot.src.logs import logger

status_blacklist: list = ["conversation",
                        "sysprompt", "user_id",
                        "user_ids_index", "embedding_model",
                        "last_seen", "debug"
                    ]
max_kilobytes = 24

class UserPrepare():
    def __init__(self) -> None:        
        self.session_tokens: int = 0

        self.chat_model: str = co.session_default_chat_model
        self.img_model: str = co.session_default_img_model
        self.improve_model: str = conf.text_improve_model
        self.vision_model: str = conf.default_vision_model
        self.tool_model: str = conf.default_tool_model
        self.embedding_model: str = conf.default_embedding_model

        self.memory: bool = True

        self.used_tokens: int = 0

        self.transcribe: bool = False
        self.answer_stt: bool = False
        self.stt_language = None

        self.max_tokens: int = 1024

        self.temperature: float = 1.0
        self.top_p: float = 1.0
        self.frequency_penalty: float = 0.0
        self.presence_penalty: float = 0.0
        self.seed: int | None = None

        self.group_mode: bool = False
        self.random_names: bool = True

        self.streaming: bool = True
        self.timeout: float = 6.0
        self.roleplaying: bool = False
        self.randomizer: bool = False
        self.summarize: bool = True
        self.tool_call: bool = False

        self.tts_voice: str = conf.default_tts_voice
        self.to_tts: bool = False

        self.groups: set = set()
        self.owners: set = set()

        self.sysprompt: str = ""

        self.user_id: str  = ''
        self.user_ids_index: dict = dict()
        self.last_seen: datetime = datetime.now()
        self.debug: bool = False
        self.conversation: list[dict] = self.get_custom_sysprompt()

    async def from_dict(self, data):
        for key, value in data.items():
            # Deserialize the value from JSON
            try:
                value = loads(value)
                if isinstance(value, dict) and 'type' in value:
                    data_type = value['type']
                    value_data = value['value']
                    match data_type:
                        case 'set':
                            value = set(value_data)
                        case 'bool':
                            value = bool(value_data)
                        case 'datetime':
                            value = datetime.fromisoformat(value_data)
                        case 'int':
                            value = int(value_data)
                        case 'float':
                            value = float(value_data)
                        case 'list' | 'dict':
                            value = loads(value_data)
                        case 'none':
                            value = None
                        case _:
                            value = value_data
            except JSONDecodeError as e:
                # Handle the case where JSON decoding fails
                raise ValueError(f"Error decoding JSON for key {key}") from e

            self.__dict__[key] = value

    def to_string(self):
        lines = []

        blist = status_blacklist.copy()
        if self.roleplaying:
            blist.extend(["chat_model"])
        if not self.group_mode:
            blist.extend(["group_mode", "random_names"])
        if not self.tool_call:
            blist.extend(["tool_model"])

        for key, value in vars(self).items():
            if key in ["groups", "owners"]:
                value = len(value)
                if not value:
                    continue
            elif key in blist:
                continue
            lines.append(f'{key}: {value!r}')
        return '\n'.join(lines[:-1]) + '\n'

    def get_custom_sysprompt(self) -> list[dict]:
        if self.sysprompt == "empty":
            return list()
    
        new_system = f'{self.sysprompt if self.sysprompt else conf.bot_prompts.get("system", "")}'
        if self.tool_call:

            new_system += "\n\nRemember to use"
            new_system += f" ({', '.join(f'{tool}' for tool in co.tools_loaded)}) "
            new_system += "tools if user ask something related to its capabilities."
            new_system += " Answers in the same user language."

        liste = [{"role": "system", "content": new_system}]

        if self.roleplaying:
            liste.extend([{"role": "user", "content": "🫡"},{"role": "assistant", "content": "🫡"}])
        return liste

    async def request_wrap(self, event, user_id, command = None) -> None:
        task_id = await self.random_uuid(str(event.chat_id), user_id)
        transcribed = None
        file_meta: dict = await check_media_type(event)
        if command == conf.command_image:
            return await img_wrap(
                self, event, user_id, command, task_id
                )
        elif file_meta["type"] == "audio":
            if command == conf.command_stt or (self.transcribe and command == conf.command_transcribe):
                transcribed = await stt_wrap(self, event, user_id, task_id)
                if not transcribed:
                    return
            else:
                return
        elif command == "/vision" and file_meta["type"] != "image":
            await event.reply("👁️📷❓")
            return
        elif command == "/tts":
            return await tts_wrap(
                self, event, user_id, command, task_id
                )

        return await ask_wrap(
            self, event, user_id, transcribed,
            command, task_id, file_meta
            )

    async def delete_conversation(self, event=None, user_id=None, rol = 0, notify = 0, summarized = 0):
        if (event and self.memory and self.group_mode and
            user_id and user_id not in self.owners and notify):
            return await event.reply("🚫🫂🚫")

        if not rol and self.roleplaying:
            self.sysprompt = ""
            self.roleplaying = False
            self.chat_model = conf.default_chat_model
            self.temperature = 1.0
            self.top_p = 1.0
        self.conversation = self.get_custom_sysprompt()
        self.session_tokens = 0
        if self.random_names and not summarized:
            self.user_ids_index = dict()
    
    async def handle_summarize(self, user_id, conversation_text = None):
        try:
            logger.info("Trying to summarize the conversation.")
            tempbak = float(self.temperature)
            latest_msgs = []
            if len(self.conversation) > 5:
                #for msg in self.conversation:
                    #if msg["role"] in ["user"]:
                        
                latest_msgs = self.conversation[-5:]
            else:
                latest_msgs = self.conversation[-1:]
            #latest_msgs.append(self.conversation[-1:][0])
            conversation_context = await get_conversation(self, user_id=user_id, summary=True)
            await self.delete_conversation(summarized = 1)
            self.temperature = tempbak
            self.conversation.append(conversation_context)
            self.conversation.extend(latest_msgs)
            return conversation_text
        except Exception as e:
            raise Exception(f'handle_summarize: {str(e)}') from e

    async def tokens_counter(self, user_id):
        try:
            current_token_length = await calculate_token_length(self.conversation)
            conversation_text = None
            if current_token_length > int(self.max_tokens):
                logger.info(f"Detected token limit: {current_token_length}:{self.max_tokens}")
                if self.summarize and not self.roleplaying:
                    conversation_text = await self.handle_summarize(user_id)
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

    async def update_session_tokens(self, event, user_id, response, tokens_used: int):
        self.used_tokens += tokens_used
        svars.total_tokens += tokens_used
        self.session_tokens = await calculate_token_length(self.conversation)
        if response:
            logger.info(f"💰 {svars.total_tokens} 💰")
        if not self.memory:
            await self.delete_conversation(event, user_id)

    async def group_mode_data_fetch(self, event):
        try:
            user_id = await get_id(event)
            if user_id not in self.user_ids_index:
                if self.random_names:
                    self.user_ids_index[user_id] = await self.gen_random_name()
                else:
                    user_data: RequestedPeerUser = await conf.bot.get_entity(int(user_id)) # type: ignore
                    new_name = (user_data.first_name if user_data.first_name
                                else user_data.username if user_data.username
                                else ""
                                )
                    new_name = await self.normalize_text(new_name)
                    new_name = str(sub(r'[^a-zA-Z0-9 _\-\.@]', '', new_name)).strip()

                    if not new_name:
                        new_name = await self.gen_random_name()

                    self.user_ids_index[user_id] = new_name
            return self.user_ids_index[user_id]
        except Exception as e:
            logger.error(f"group_mode_data_fetch: {str(e)}")
            return await self.gen_random_name()

    async def extract_prompt(self, event, user_id, command, transcription, buttons, file_meta):
        
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
            thisShit = await extract_arguments(self, event, prompt, command, user_id, file_meta=file_meta)

            if not thisShit:
                return None, None, None
            else:
                prompt = thisShit.prompt
            if self.group_mode:
                prompt = f'{await self.group_mode_data_fetch(event)} says: {prompt}'
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
            if self.check_size(file_meta["size"]) and (file_meta["type"] == "text" or file_meta["mime"] in conf.allowed_chat_mimetypes):
                file_meta = await extract_media(event, file_meta)
                list_convo.append({"role": "user", "content": f'{file_meta["name"]}: [{file_meta["file"].decode("utf-8")}]'})
            logger.debug(f'Returning prompt: {list_convo}')
            return placeholder_msg, list_convo, thisShit
        except Exception as e:
            raise Exception (f"extract_prompt: {str(e)}")



    @staticmethod
    async def random_uuid(chat_id, user_id):
        tid = str(uuid4())[:6]
        if user_id == chat_id:
            tid += "✦"
        return tid

    @staticmethod
    def check_size(size):
        return int(size) <= max_kilobytes * 1024

    @staticmethod
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

    @staticmethod
    async def normalize_text(text):
        try:
            return ''.join(
                c for c in normalize('NFKD', text) 
                if category(c) != 'Mn')
        except Exception as e:
            raise Exception(f"normalize_text: {str(e)}")
