import bot.src.tools.api_utils.apis_frontend as gptools
from asyncio import wait_for
from bot.src.handlers.tasks import add_task, gen_cancel_button as gcb
from bot.src.logs import logger
from bot.src.tools.tg_tools import send_msg, remove_command, edit_msg
from bot.src.tools.params.inference_params import extract_arguments
from sys import _getframe

async def img_wrap(self, event, user_id, chat_id, command, task_id):
    
    
    prompt = await remove_command(self.conversation, event, command)

    thisShit = await extract_arguments(self, event, prompt, command, user_id)
    if not thisShit:
        return None

    placeholder_msg = await event.reply("🤔🎨, 🖐️⏳...", buttons = await gcb(command, task_id))

    task = do_img(thisShit, user_id, event, placeholder_msg, command)
    msg = await add_task(command, user_id, chat_id, task, task_id)
    if msg == "CantAddMore":
        return await edit_msg(event, placeholder_msg, "🫵🤬, 🖐️⏳... 🖕.")
    return None

async def do_img(thisShit, user_id, event, placeholder_msg, command):
    images = None
    responseapi = gptools.call_api(thisShit, command = command, user_id = user_id)
    images, resos, status = await wait_for(responseapi.__anext__(), 60)
    if status == "cancel":
        await placeholder_msg.delete()
        return "cancel"

    if isinstance(images, list):
        async with event.client.action(entity=event.chat_id, action='photo'):
            
            caption = await make_caption(thisShit, resos)
            if thisShit.raw:
                ForceFile = True
            else:
                ForceFile = False

            await send_msg(event,
                           caption,
                            file=images,
                            force_document=ForceFile,
                            disable_delete=True
                            )
            await placeholder_msg.delete()

    elif isinstance(images, str):
        await edit_msg(event, placeholder_msg, images)
    return


async def make_caption(data, resos):
    try:
        caption = ""
        if len(data.prompt) < 800:
            caption += f'✍️ `{data.prompt}`\n\n'
        caption += f'👗 `{data.style_data[0]}`\n'
        caption += f'🤖 `{data.img_model}`'
        caption += f'\n📐 `{resos[0]}`'
        return caption
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
