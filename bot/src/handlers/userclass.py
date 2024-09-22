from json import loads, JSONDecodeError
from datetime import datetime
from uuid import uuid4

from bot.src.config import (bot_prompts, command_image, command_stt,default_chat_model, default_img_model, default_vision_model,
                            text_improve_model, command_transcribe, default_tool_model, default_embedding_model,
                            default_tts_voice)
from bot.src import constants as co
from bot.src.tools.tg_tools import check_media_type
from bot.src.handlers.commands.stt import stt_wrap
from bot.src.handlers.commands.img import img_wrap
from bot.src.handlers.commands.tts import tts_wrap
from bot.src.handlers.commands.ask import ask_wrap


status_blacklist: list = ["conversation",
                        "sysprompt", "user_id",
                        "user_ids_index", "embedding_model",
                        "last_seen", "debug"
                    ]

class UserPrepare():
    def __init__(self) -> None:        
        self.session_tokens: int = 0

        self.chat_model: str = co.session_default_chat_model
        self.img_model: str = co.session_default_img_model
        self.improve_model: str = text_improve_model
        self.vision_model: str = default_vision_model
        self.tool_model: str = default_tool_model
        self.embedding_model: str = default_embedding_model

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
        self.roleplaying: bool = False
        self.randomizer: bool = False
        self.summarize: bool = True
        self.tool_call: bool = False

        self.tts_voice: str = default_tts_voice
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
                else:
                    value = value
            except JSONDecodeError:
                # Handle the case where JSON decoding fails
                raise ValueError(f"Error decoding JSON for key {key}")

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

    def get_custom_sysprompt(self, liste = []) -> list[dict]:
        if self.sysprompt != "empty":
            new_system = f'{self.sysprompt if self.sysprompt else bot_prompts.get("system", "")}'
            if self.tool_call:

                new_system += f"\n\nRemember to use ({', '.join(f'{tool}' for tool in co.tools_loaded)}) "
                new_system += "tools if user ask something related to its capabilities. Answers in the same user language."

            liste = [{"role": "system", "content": new_system}]

            if self.roleplaying:
                liste.extend([{"role": "user", "content": "🫡"},{"role": "assistant", "content": "🫡"}])
        return liste

    async def request_wrap(self, event, user_id, command = None) -> None:
        task_id = await self.random_uuid(str(event.chat_id), user_id)
        transcribed = None
        file_meta: dict = await check_media_type(event)
        if command == command_image:
            return await img_wrap(self, event, user_id, command, task_id)
        elif file_meta["type"] == "audio":
            if command == command_stt or (self.transcribe and command == command_transcribe):
                transcribed = await stt_wrap(self, event, user_id, task_id)
                if not transcribed:
                    return
            else:
                return
        elif command == "/vision" and file_meta["type"] != "image":
            await event.reply("👁️📷❓")
            return
        elif command == "/tts":
            return await tts_wrap(self, event, user_id, command, task_id)

        return await ask_wrap(self, event, user_id, transcribed, command, task_id, file_meta)

    async def delete_conversation(self, event=None, user_id=None, rol = 0, notify = 0, summarized = 0):
        if (event and self.memory and self.group_mode and
            user_id and user_id not in self.owners and notify):
                return await event.reply("🚫🫂🚫")

        if not rol and self.roleplaying:
            self.sysprompt = ""
            self.roleplaying = False
            self.chat_model = default_chat_model
            self.temperature = 1.0
            self.top_p = 1.0

        self.conversation = self.get_custom_sysprompt()
        self.session_tokens = 0
        if self.random_names and not summarized:
            self.user_ids_index = dict()

    @staticmethod
    async def random_uuid(chat_id, user_id):
        tid = str(uuid4())[:6]
        if user_id == chat_id:
            tid += "✦"
        return tid
