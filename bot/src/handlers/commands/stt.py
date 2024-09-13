import bot.src.tools.api_utils.apis_frontend as gptools
from bot.src.tools.tg_tools import check_media_type, send_msg
from subprocess import call
from tempfile import TemporaryDirectory
from pathlib import Path
from asyncio import wait_for, CancelledError
from bot.src.logs import logger
from bot.src.handlers.commands.tasks import add_task, gen_cancel_button as gcb
from bot.src.config import command_stt
from io import BytesIO
import subprocess
from tempfile import NamedTemporaryFile
import os
from . import extract_media, edit_msg, remove_command


async def stt_wrap(self, event, user_id, task_id, command = command_stt):
    from bot.src.tools.params.inference_params import extract_arguments
    placeholder_msg = None
    thisShit = None
    file_meta = await check_media_type(event)
    
    prompt = await remove_command(self.conversation, event, command)
    thisShit = await extract_arguments(self, event, prompt, command, user_id, file_meta = file_meta)
    if file_meta["type"] == "audio":
        placeholder_msg = await event.reply("🤔🎤, 🖐️⏳...", buttons = await gcb(command, task_id))
        file_meta = await extract_media(event, file_meta, placeholder_msg)
    if not placeholder_msg:
        return None
    task = do_stt(thisShit, event, file_meta, user_id, placeholder_msg, command)
    msg = await add_task(command, user_id, task, task_id)
    if msg == "CantAddMore":
        await edit_msg(event, placeholder_msg, "🫵🤬, 🖐️⏳... 🖕.")
    return msg


async def do_stt(thisShit, event, file_meta, user_id, placeholder_msg, command):

    try:

        async with event.client.action(entity=event.chat_id, action='typing'):
            transcribed = None
            await edit_msg(event, placeholder_msg, "🔽🆗, 🖐️⏳...")
            transcribed = await process_audio(thisShit, event, user_id, placeholder_msg, file_meta=file_meta, command = command)
            if transcribed == "Cancelled":
                return None
            if len(transcribed) > 4080:
                await placeholder_msg.delete()
                chunks = [transcribed[i:i+4080] for i in range(0, len(transcribed), 4080)]
                for i, chink in enumerate(chunks):
                    await event.reply(f'🎤 ({i+1}/{len(chunks)}) {chink}')
            else:
                await edit_msg(event, placeholder_msg, text = f'🎤 {transcribed}')

            if thisShit.answer_stt:
                return transcribed
            return
    except Exception as e:
        logger.error(f"Error in do_stt: {str(e)}")
        await edit_msg(event, placeholder_msg, text = "🎤 😔❌👍")
        return None

async def process_audio(thisShit, event, user_id, placeholder_msg, file_meta, command):
    try:
        logger.debug("Recibido audio!")
        media = None
        triggered = None
        if file_meta["mime"] not in ["ogg", "mpeg"]:
            media = await transcode_audio(file_meta)
            triggered = True
        else:
            media = file_meta["file"]

        if media:
            media = [triggered, media]
            await edit_msg(event, placeholder_msg, "✍️🎤...")
            try:
                responseapi = gptools.call_api(thisShit, command = command, user_id=user_id, media = media)
                response, status = await wait_for(responseapi.__anext__(), 60) # type: ignore
                if status == "done":
                    return response
                elif status == "fail":
                    await edit_msg(event, placeholder_msg, "🎤 😔❌👍")
            except CancelledError:
                await placeholder_msg.delete()
                return "Cancelled"

    except Exception as e:
        raise Exception(f'process_audio: {str(e)}')

async def transcode_audio(file_meta):
    try:
        with NamedTemporaryFile(suffix=Path(file_meta["name"]).suffix, delete=True) as doc_file:
            doc_file.write(file_meta["file"])
            doc_file.flush()

            with NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
                command = [
                    "sox",
                    doc_file.name,
                    "-c", "1",
                    "-r", "16000",
                    "-q", ogg_file.name
                ]
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                ogg_file.seek(0) # type: ignore
                audio_data = BytesIO(ogg_file.read())

                ogg_file.close()
                os.remove(ogg_file.name)

            return audio_data

    except subprocess.CalledProcessError as e:
        raise Exception(f'transcode_audio: SoX failed with exit code {e.returncode}')
    except Exception as e:
        raise Exception(f'transcode_audio: {str(e)}')
        
        
        
async def transcode_audio_2(file_meta):
    try:
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            doc_path = tmp_dir / Path(file_meta["name"])
            logger.debug(f"Doc path: {doc_path}")
            with open(doc_path, "wb") as f:
                f.write(file_meta["file"])
            ogg_file_path = tmp_dir / "voice.ogg"
            call(f"sox {doc_path} -c 1 -r 16000 -q {ogg_file_path} > /dev/null 2>&1", shell=True)
            logger.debug(f"OGG path: {ogg_file_path}")
            with open(ogg_file_path, "rb") as f:
                return BytesIO(f.read())
    except Exception as e:
        raise Exception(f'transcode_audio: {str(e)}')