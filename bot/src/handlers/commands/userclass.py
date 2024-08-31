from subprocess import call
from tempfile import TemporaryDirectory
from pathlib import Path
from asyncio import sleep, wait_for
from telethon.errors.rpcerrorlist import MessageNotModifiedError, MessageEmptyError
from telethon.events import NewMessage
from telethon.types import MessageMediaPhoto, MessageMediaDocument
import bot.src.tools.api_utils.gpt as gptools
from bot.src.tools.tg_lib.mini_tools import remove_command

import base64
import random

from bot.src.logs import logger
from time import time
from copy import deepcopy
from bot.src.constants import models_dict, img_models, whisper_models
from bot.src.config import default_chat_model, default_img_model, default_stt_model

beauty_list = {}

vision_models = [model for model in models_dict.keys() if "vision" in model]


master_prompt = {"role": "system",
"content": "adapts the personality to user's one (answer the next text in the same language.)"}

status_blacklist = ["conversation",
                       "whisper_model", "whisper_api",
                       "img_api", "sysprompt"]

class UserPrepare():
    def __init__(self) -> None:
        self.used_tokens = 0
        self.model = default_chat_model
        self.img_model = default_img_model
        self.streaming = True
        self.answer_stt = False
        self.chat_pending = False
        self.img_pending = False
        self.roleplaying = False
        self.memory = True
        self.max_tokens = 4096
        self.seed = None
        self.temperature = 1
        self.top_p = 1
        self.frequency_penalty = 0
        self.presence_penalty = 0
        self.randomizer = False
        self.sysprompt = None
        self.whisper_model = default_stt_model
        self.whisper_api = "openai"
        self.img_api = "openai"
        self.conversation = [deepcopy(master_prompt)]

    async def to_string(self):
        lines = []
        for key, value in vars(self).items():
            if self.roleplaying:
                blist = status_blacklist.copy()
                blist.extend(["model"])
            else:
                blist = status_blacklist
            if key in blist: continue
            lines.append(f'{key}: {value!r}')
        return '\n'.join(lines[:-1]) + '\n'

    async def get_custom_sysprompt(self) -> list:
        return [deepcopy(self.sysprompt) if self.sysprompt else deepcopy(master_prompt)]

    async def request_wrap(self, event: NewMessage, command = None) -> None:
        if command in ["/img"]:
            prompt = await remove_command(self.conversation, event, command)
            if len(prompt) < 1:
                return await event.reply("🎨❓")
            elif len(prompt) > 1999:
                await event.reply("🚫... ✂️✍️✂️💌✂️🙊")
                prompt = prompt[:2000]
            models_to_check = img_models.keys() if not img_models.get(self.img_model) else [self.img_model]
            self.img_pending = True
            placeholder_msg = await event.reply("🤔🎨, 🖐️⏳...")
            while self.img_pending:
                for model in models_to_check:
                    temp_apis = img_models[model].copy()
                    random.shuffle(temp_apis)
                    logger.debug(f"apis for images {temp_apis}")
                    for self.img_api in img_models[model]:
                        try:
                            responseapi = gptools.call_api(self, type = "img", media = prompt)
                            response, nprompt = await wait_for(responseapi.__anext__(), 60)
                        except: continue
                        if isinstance(response, list):
                            async with event.client.action(entity=event.chat_id, action='photo'):
                                if len(nprompt) > 980:
                                    nprompt = f'{nprompt[:1019]}...✂️'
                                else:
                                    nprompt = f'✍️ `{nprompt}`\n\n🤖 `{self.img_model}`'
                                await event.reply(nprompt,
                                                file=response,
                                                force_document=False,
                                                )

                            self.img_pending = False
                            break
                else:
                    break
            if self.img_pending:
                await event.reply("🎨 😔❌👍")
            await placeholder_msg.delete()
            self.img_pending = False
            return

        async with event.client.action(entity=event.chat_id, action='typing'):
            transcribed = None
            doc = None
            file_bytes = None
            mimetype = None
            if command in ["/stt", "/vision"]:
                replied = await event.get_reply_message()

                media = event.message.media if event.message.media else replied.media if replied and replied.media else None
                match media:
                    case MessageMediaDocument():
                        doc = media.document
                        if doc.mime_type.startswith("audio/"):
                            transcribed = await self.process_audios(event, target = doc)
                            if not self.answer_stt:
                                if len(transcribed) > 4080:
                                    chunks = [transcribed[i:i+4080] for i in range(0, len(transcribed), 4080)]
                                    for i, chink in enumerate(chunks):
                                        await event.reply(f'🎤 ({i+1}/{len(chunks)}) {chink}')
                                else:
                                    await event.reply(f'🎤 {transcribed}')
                                return

                        doc = None
                    case MessageMediaPhoto():
                        mimetype = "jpeg"
                        media = media.photo

                    case _:
                        doc = None

            if mimetype:
                file_bytes = await event.client.download_media(media, file=bytes)
                doc = f"data:image/{mimetype};base64,{base64.b64encode(file_bytes).decode('utf-8')}"
            return await self.chat_completion(event, transcription = transcribed, vision = doc, command = command)

    async def retry_wrap(self, event, command = None) -> None:
        if len(self.conversation) > 1:
            return await self.chat_completion(event, retry = True, command = command)
        return await event.reply("🙄")

    async def delete_conversation(self, rol = 0):
        if not rol and self.roleplaying:
            self.sysprompt = None
            self.roleplaying = False
            self.model = default_chat_model
        self.conversation = await self.get_custom_sysprompt()
        self.used_tokens = 0

    async def chat_completion(self, event, transcription = None, retry = None, vision: str | None = None,  command: None | str = None) -> None:
        logger.debug(command)
        if not retry:
            if not isinstance(transcription, str):

                    prompt = await remove_command(self.conversation, event, command)

                    if len(prompt) < 1:
                        if self.roleplaying:
                            return await event.reply("🔞❓")
                        return await event.reply("❓")

                    if not self.memory:
                        self.used_tokens = 0
                        self.conversation = await self.get_custom_sysprompt()

            else:
                prompt = transcription

            dict_add = {"role": "user", "content": prompt}
            if vision:
                dict_add["content"] = [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": vision}}
                    ]
            self.conversation.append(dict_add)

        logger.debug(f"Convo length: {len(self.conversation)}")
        if len(self.conversation) > 17:
            logger.debug(f"Detected limit. deleting old messages.")
            for i, msg in enumerate(self.conversation):
                if msg["role"] in ["user", "assistant"]:
                    del self.conversation[i]
                    if len(self.conversation) <= 17:
                        break
        logger.debug(f"Convo length: {len(self.conversation)}")

        logger.debug(self.conversation)

        self.chat_pending = True
        old_text = ""
        done_parts = []

        wait_message = await event.reply("...🤔")
        logger.debug("Petición")

        temp_apis = False
        
        if models_dict:
            temp_apis = models_dict[self.model].copy()
        else:
            temp_apis = beauty_list[str(self.roleplaying)].copy()
        random.shuffle(temp_apis)
        logger.debug(f"apis for chat {temp_apis}")
        for self.api in temp_apis:
            try:
                logger.debug("Calling api")
                responseapi = gptools.call_api(self, "chat")
                logger.debug("Continuing api processing")
                status = ""
                response = ""

                start_time = time()
                while self.chat_pending:
                    logger.debug("inside while")
                    try:
                        try:
                            logger.debug("wait_for api")
                            response, status = await wait_for(responseapi.__anext__(), timeout = 60)
                            logger.debug("wait_for api-post")

                        except:
                            raise
                        end_time = time()
                        time_diff = end_time - start_time
                        logger.debug("calculating times")
    
                        if time_diff < 0.5 and status not in ["stop", "error"]: continue
                        elif status in ["stop", "error"]:
                            raise StopAsyncIteration("internal status break")
                        else:
                            if len(response) > 1:
                                old_text = response
                                if len(response) > 4080:
                                    chunks = [response[i:i+4080] for i in range(0, len(response), 4080)]
                                    for i, chink in enumerate(chunks):
                                        if i not in done_parts:
                                            wait_message = await event.reply("...🤔")
                                            await event.client.edit_message(entity = event.chat_id, message = wait_message, text = chink)
                                            done_parts.append(i)
                                        continue
                                else:
                                    await event.client.edit_message(entity = event.chat_id, message = wait_message, text = f'{response}...🤔')
                            await sleep(0.02)
                            start_time = time()
                    except (MessageNotModifiedError, MessageEmptyError):
                        pass
                    except StopAsyncIteration:
                        if status == "error":
                            response = f'{old_text}... {response}'
                        if len(response) > 4080:
                            chunks = [response[i:i+4080] for i in range(0, len(response), 4080)]
                            await event.client.edit_message(entity = event.chat_id, message = wait_message, text = chunks[0])
                            done_parts.append(0)
                            for i, chink in enumerate(chunks):
                                if i not in done_parts:
                                    await event.reply(chink)
                                    done_parts.append(i)
                                continue
                        else:
                            await event.client.edit_message(entity = event.chat_id, message = wait_message, text = response)
                        if self.memory: self.conversation.append({"role": "assistant", "content": response})
                        logger.info(f"💰 {gptools.total_tokens} 💰")
                        self.chat_pending = False
                    except Exception as e:
                        raise ConnectionError(f"Bucle completion: {e}")

                break
            except PermissionError as e:
                logger.error(e[0])
                logger.debug(e[1])
                continue
            except Exception as e:
                logger.error(f"Error with {self.api}: {str(e)}")
                continue
        else:
            await event.client.edit_message(entity = event.chat_id, message = wait_message, text = '✍️ 😔❌👍')
        self.chat_pending = False

    async def process_audios(self, event, target):
        logger.debug("Recibido audio!")
        with TemporaryDirectory() as tmp_dir:
            placeholder_msg = await event.reply("🤔🎤, 🖐️⏳...")
            file_bytes = await event.client.download_media(target, file=bytes)
            mimetype = target.mime_type.split("/")[1]

            tmp_dir = Path(tmp_dir)
            doc_path = tmp_dir / Path("tempaudio." + mimetype)
            logger.debug(f"Doc path: {doc_path}")
            with open(doc_path, "wb") as f:
                f.write(file_bytes)
            mp3_file_path = tmp_dir / "voice.mp3"
            call(f"sox {doc_path} -c 1 -r 16000 -q {mp3_file_path} > /dev/null 2>&1", shell=True)
            logger.debug(f"MP3 path: {mp3_file_path}")
            models_to_check = whisper_models.keys() if not whisper_models.get(self.whisper_model, False) else [self.whisper_model]
            ok = False
            while not ok:
                for model in models_to_check:
                    temp_apis = whisper_models[model].copy()
                    random.shuffle(temp_apis)
                    logger.debug(f"apis for transcription {temp_apis}")
                    for self.whisper_api in temp_apis:
                        try:
                            responseapi = gptools.call_api(self, type = "stt", media = mp3_file_path)
                            response, status = await wait_for(responseapi.__anext__(), 60)
                            if status == "done":
                                ok = True
                                break
                            else: continue
                        except: continue
                else:
                    break
                

            if not ok:
                await event.reply("🎤 😔❌👍")
            await placeholder_msg.delete()
            return response
    