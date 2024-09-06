
from telethon.events import NewMessage
from uuid import uuid4
from copy import deepcopy
from bot.src.config import (default_chat_model, default_img_model, bot_prompts,
                            command_image, text_improve_model, command_stt,
                            default_vision_model)
from bot.src.handlers.commands.img import img_wrap
from bot.src.handlers.commands.stt import stt_wrap
from bot.src.handlers.commands.ask import ask_wrap
from bot.src.tools.tg_tools import check_media_type
#from bot.src.logs import logger

master_prompt = {"role": "system",
"content": bot_prompts.get("system", "")}

status_blacklist = ["conversation",
                       "whisper_model", "whisper_api",
                       "img_api", "sysprompt", "user_id",
                       "user_ids_index"
                    ]

class UserPrepare():
    def __init__(self) -> None:
        self.group_mode = False
        self.random_names = True
        self.used_tokens = 0
        self.chat_model = default_chat_model
        self.img_model = default_img_model
        self.improve_model = text_improve_model
        self.vision_model = default_vision_model
        self.streaming = True
        self.answer_stt = False
        self.roleplaying = False
        self.memory = True
        self.max_tokens = 2048
        self.seed = None
        self.temperature = 1
        self.top_p = 1
        self.frequency_penalty = 0
        self.presence_penalty = 0
        self.randomizer = False
        self.sysprompt = None
        self.user_id = None
        self.user_ids_index = {}
        self.conversation = self.get_custom_sysprompt()

    def to_string(self):
        lines = []

        blist = status_blacklist.copy()
        if self.roleplaying:
            blist.extend(["chat_model"])
        if not self.group_mode:
            blist.extend(["group_mode", "random_names"])

        for key, value in vars(self).items():
            if key in blist:
                continue
            lines.append(f'{key}: {value!r}')
        return '\n'.join(lines[:-1]) + '\n'

    def get_custom_sysprompt(self) -> list:
        return [deepcopy(self.sysprompt if self.sysprompt else master_prompt),
                {"role": "user", "content": "🫡"},{"role": "assistant", "content": "🫡"}]

    async def request_wrap(self, event: NewMessage, command = None) -> None:
        task_id = await random_uuid()
        transcribed = None
        file_meta = await check_media_type(event)
        if command == command_image:
            return await img_wrap(self, event, command, task_id)
        elif file_meta["type"] == "audio" or command == command_stt:
            transcribed = await stt_wrap(self, event, task_id)
            if not transcribed:
                return

        return await ask_wrap(self, event, transcribed, command, task_id, file_meta)

    async def delete_conversation(self, event, user_id, rol = 0):
        if self.user_id != user_id:
            return await event.reply("🚫🫂🚫")
        if not rol and self.roleplaying:
            self.sysprompt = None
            self.roleplaying = False
            self.chat_model = default_chat_model
            self.temperature = 1
            self.top_p = 1

        self.conversation = self.get_custom_sysprompt()
        self.used_tokens = 0


async def random_uuid():
    return str(uuid4())[:6]