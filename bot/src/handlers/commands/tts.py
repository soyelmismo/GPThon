import bot.src.tools.api_utils.apis_frontend as gptools
from asyncio import wait_for
from bot.src.handlers.tasks import add_task, gen_cancel_button as gcb
from bot.src.logs import logger
from bot.src.tools.tg_tools import send_msg, remove_command, edit_msg
from bot.src.tools.params.inference_params import extract_arguments
from io import BytesIO

async def tts_wrap(self, event, user_id, chat_id, command, task_id, bot_response = None):

    if not bot_response:
        prompt = await remove_command(self.conversation, event, command)
    else:
        prompt = bot_response

    thisShit = await extract_arguments(self, event, prompt, command, user_id)
    if not thisShit:
        return None

    placeholder_msg = await event.reply("🗣, 🖐️⏳...", buttons = await gcb(command, task_id))
    task = do_tts(thisShit, user_id, event, placeholder_msg, command)
    msg = await add_task(command, user_id, task, task_id)
    if msg == "CantAddMore":
        return await edit_msg(event, placeholder_msg, "🫵🤬, 🖐️⏳... 🖕.")
    return

async def do_tts(thisShit, user_id, event, placeholder_msg, command):
    audio = None
    try:
        responseapi = gptools.call_api(thisShit, command = command, user_id = user_id)
        audio, status = await wait_for(responseapi.__anext__(), 60)
        if status == "fail":
            await edit_msg(event, placeholder_msg, audio)
        elif status == "cancel":
            await placeholder_msg.delete()
            return status
    except Exception as e:
        logger.error(f'Error tts: {str(e)}')
        await edit_msg(event, placeholder_msg, "🗣 😔❌👍")

    if isinstance(audio, BytesIO):
        caption = None
        async with event.client.action(entity=event.chat_id, action='photo'):
            # if self.to_tts:
            #     caption = text_response
            await send_msg(event, caption,
                            file=audio,
                            force_document=False,
                            disable_delete=True
                            )
            if command == "/tts":
                await placeholder_msg.delete()

    elif isinstance(audio, str):
        await edit_msg(event, placeholder_msg, audio)
    return
