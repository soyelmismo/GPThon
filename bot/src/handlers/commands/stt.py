import bot.src.tools.api_utils.apis_frontend as gptools
from bot.src.tools.tg_tools import check_media_type, extract_media, edit_msg, remove_command
from bot.src.tools.params.inference_params import extract_arguments, command_stt
from pathlib import Path
from asyncio import wait_for, create_subprocess_exec, subprocess
from bot.src.logs import logger
from bot.src.handlers.tasks import add_task, gen_cancel_button as gcb
from bot.src.config import command_stt
from tempfile import NamedTemporaryFile

from io import BytesIO
import os


async def stt_wrap(self, event, user_id, task_id, command = command_stt):

    placeholder_msg = None
    thisShit = None
    buttons = None
    command, file_meta = await check_media_type(self, event, command, self.transcribe)

    prompt = await remove_command(self.conversation, event, command)
    thisShit = await extract_arguments(self, event, prompt, command, user_id, file_meta = file_meta)
    if file_meta["type"] == "audio" and file_meta["size"]:
        buttons = await gcb(command, task_id)
        placeholder_msg = await event.reply("🤔🎤, 🖐️⏳...", buttons = buttons)
    if not placeholder_msg:
        return None
    task = do_stt(thisShit, event, file_meta, user_id, placeholder_msg, command, buttons)
    msg = await add_task(command_stt, user_id, task, task_id)
    if msg == "CantAddMore":
        await edit_msg(event, placeholder_msg, "🫵🤬, 🖐️⏳... 🖕.")
    if msg is not None:
        self.daily[command_stt]["current"] += file_meta.get("duration", 0)
    return msg


async def do_stt(thisShit, event, file_meta, user_id, placeholder_msg, command, buttons = None):
    transcribed = None
    try:

        async with event.client.action(entity=event.chat_id, action='typing'):
            file_meta = await extract_media(thisShit, event, file_meta, placeholder_msg, buttons)
            if isinstance(file_meta, str) and file_meta == "Task_cancellled":
                await placeholder_msg.delete()
                return None
            await edit_msg(event, placeholder_msg, "🔽🆗, 🖐️⏳...", buttons)
            transcribed = await process_audio(thisShit, event, user_id, placeholder_msg, file_meta=file_meta, command = command, buttons = buttons)
            if str(transcribed) == "Cancelled":
                return None
            if isinstance(transcribed, str) and len(transcribed) > 4080:
                await placeholder_msg.delete()
                chunks = [transcribed[i:i+4080] for i in range(0, len(transcribed), 4080)]
                for i, chink in enumerate(chunks):
                    await event.reply(f'🎤 ({i+1}/{len(chunks)}) {chink}')
            else:
                await edit_msg(event, placeholder_msg, text = f'🎤 {transcribed}')

            if thisShit.answer_stt:
                return transcribed
            return True
    except Exception as e:
        logger.error(f"Error in do_stt: {str(e)}")
        await edit_msg(event, placeholder_msg, text = "🎤 😔❌👍")
        return None

async def process_audio(thisShit, event, user_id, placeholder_msg, file_meta, command, buttons):
    try:
        logger.debug("Recibido audio!")
        media = None
        triggered = None
        if file_meta["mime"] not in ["ogg", "mpeg", "aac", "m4a", "mp4a", "mp4a-latm"]:
            media = await transcode_audio(file_meta)
            triggered = True
        else:
            media = file_meta["file"]

        if media:
            media = [triggered, media]
            await edit_msg(event, placeholder_msg, "✍️🎤...", buttons)
            responseapi = gptools.call_api(thisShit, command = command, user_id=user_id, media = media)
            response, status = await wait_for(responseapi.__anext__(), 60) # type: ignore
            if status == "stop":
                return response.strip()
            elif status == "fail":
                await edit_msg(event, placeholder_msg, "🎤 😔❌👍")
            elif status == "cancel":
                await placeholder_msg.delete()
                return response

    except Exception as e:
        raise Exception(f'process_audio: {str(e)}')

async def transcode_audio(file_meta):
    try:
        with NamedTemporaryFile(suffix=Path(file_meta["name"]).suffix, delete=True) as doc_file:
            doc_file.write(file_meta["file"])
            doc_file.flush()

            with NamedTemporaryFile(suffix=".opus", delete=False) as opus_file:
                opus_file.close()  # Cerramos el archivo para que FFmpeg pueda acceder

                command = [
                    "ffmpeg",
                    "-i", doc_file.name,
                    "-ar", "16000",
                    "-ac", "1",
                    "-c:a", "libopus",
                    "-y",  # Sobrescribir archivo si existe
                    opus_file.name
                ]

                # Ejecutar FFmpeg de forma asíncrona
                process = await create_subprocess_exec(
                    *command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                # Esperar a que termine el proceso
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    raise Exception(f"FFmpeg error: {stderr.decode()}")

                # Leer el archivo OPUS convertido
                with open(opus_file.name, "rb") as f:
                    audio_data = BytesIO(f.read())

                os.remove(opus_file.name)

            return audio_data

    except Exception as e:
        if opus_file:
            try:
                os.remove(opus_file.name)
            except:
                pass
        raise Exception(f'transcode_audio: {str(e)}')