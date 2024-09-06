import bot.src.tools.api_utils.gpt as gptools
from bot.src.tools.tg_tools import extract_media, check_media_type, edit_msg, send_msg
from subprocess import call
from tempfile import TemporaryDirectory
from pathlib import Path
from asyncio import wait_for, CancelledError, sleep
from bot.src.logs import logger
import bot.src.constants as c
from bot.src.handlers.tasks import add_task, gen_cancel_button as gcb
from bot.src.config import default_stt_model
from io import BytesIO
import subprocess
from tempfile import NamedTemporaryFile
import os


async def stt_wrap(self, event, task_id, command = c.command_stt):

    placeholder_msg = await event.reply("🤔🎤, 🖐️⏳...", buttons = gcb(command, task_id))
    task = do_stt(self, event, placeholder_msg, command)
    msg = await add_task(command, self.user_id, task, task_id)
    if msg == "CantAddMore":
        await edit_msg(event, placeholder_msg, "🫵🤬, 🖐️⏳... 🖕.")
    return msg


async def do_stt(self, event, placeholder_msg, command):
    try:

        async with event.client.action(entity=event.chat_id, action='typing'):
            transcribed = None
            file_meta = await check_media_type(event)
            if file_meta["type"] == "audio":
                file_meta = await extract_media(event, file_meta, placeholder_msg)
                await edit_msg(event, placeholder_msg, "🔽🆗, 🖐️⏳...")
                transcribed = await process_audio(self, event, placeholder_msg, str(default_stt_model), file_meta=file_meta, command = command)        
                if transcribed == "Cancelled":
                    return None
                if len(transcribed) > 4080:
                    await placeholder_msg.delete()
                    chunks = [transcribed[i:i+4080] for i in range(0, len(transcribed), 4080)]
                    for i, chink in enumerate(chunks):
                        await event.reply(f'🎤 ({i+1}/{len(chunks)}) {chink}')
                else:
                    await edit_msg(event, placeholder_msg, text = f'🎤 {transcribed}')

                if self.answer_stt:
                    return transcribed
            else:
                await edit_msg(event, placeholder_msg, text = '🎤❔')
            return
    except Exception as e:
        logger.error(f"Error in do_stt: {str(e)}")
        await send_msg(event, "🎤 😔❌👍", delete_user_message=True)
        return None

async def process_audio(self, event, placeholder_msg, actual_model, file_meta, command):
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
            models_to_check = c.whisper_models.keys() if c.whisper_models else [actual_model]
            stt_pending = True
            await edit_msg(event, placeholder_msg, "✍️🎤...")
            while stt_pending:
                for model in models_to_check:
                    temp_apis = await gptools.shuffle_apis(self.user_id, model, command)
                    logger.debug(f"apis for transcription {temp_apis}")
                    for whisper_api in temp_apis:
                        try:
                            if triggered:
                                media.seek(0)
                            responseapi = gptools.call_api(self, type = command, media = media, api = whisper_api, model = model)
                            response, status = await wait_for(responseapi.__anext__(), 60)
                            if status == "done":
                                return response
                            else:
                                continue
                        except CancelledError:
                            await placeholder_msg.delete()
                            stt_pending = False
                            return "Cancelled"
                        except Exception as e:
                            logger.error(f'getting transcription in process_audio: {str(e)}. Continuing with other api...')
                            continue
                else:
                    break
    
        raise Exception("Oof_Fail")
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

                ogg_file.seek(0)
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