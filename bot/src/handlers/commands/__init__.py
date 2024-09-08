from bot.src.logs import logger
from .. import (bot, bot_data, bot_prompts, command_image, rate_limit_handler, command_chat,
                allowed_chat_mimetypes, get_id, max_input_tokens)
from telethon.types import DocumentAttributeSticker, DocumentAttributeVideo

async def edit_msg(event, placeholder_msg, text, buttons = None):
    return await event.client.edit_message(entity = event.chat_id, message = placeholder_msg, text = text, buttons = buttons)


async def remove_command(conversation, event, bot_command = "") -> str:
    

    message = ""
    if not isinstance(bot_command, str):
        bot_command = ""
    longrep = f"{bot_command}@{bot_data.username}"
    bot_mention = f"@{bot_data.username}"

    message = event.message.message
    msg_Attr = event.message.document.attributes if event.message.document else None
    msg_Mime = event.message.document.mime_type if event.message.document else None
    sticker = ''
    if msg_Attr:
        ok = 0
        for obj in msg_Attr:
            match obj:
                case DocumentAttributeSticker() | DocumentAttributeVideo():
                    ok = 1
            if ok and msg_Mime:
                mime = msg_Mime.split("/")[1]
                sticker = f'\n*sent .{mime} '
                
                if mime == "webm":
                    sticker += "animated sticker*"
                elif mime == "webp":
                    sticker += "sticker*"
                elif mime == "mp4":
                    sticker += "video*"
                if hasattr(obj, "alt"):
                    sticker += f': {obj.alt}'
                sticker += "\n"

                

    # Elimina bot_command, bot_command@bot_data.username y @bot_data.username
    if message.startswith(bot_command) or message.startswith(bot_mention):
        message = message.replace(longrep, "").strip()
        message = message.replace(bot_command, "").strip()
        message = message.replace(bot_mention, "").strip()

    if event.reply_to:
        replied = await event.get_reply_message()


        if replied.message:
            replied = str(replied.message).strip()
            if replied.startswith(bot_command):
                replied = str(replied).replace(longrep, "").strip()
                replied = str(replied).replace(bot_command, "").strip()
                replied = str(replied).replace(bot_mention, "").strip()
            if replied and str(conversation[-1]["content"]).strip() != replied and bot_command != command_image:
                message = str(f"\n> {replied}\n\n{message}")
            elif bot_command == command_image:
                message = str(f"{replied} {message}").strip()
    if sticker:
        message = f"{message}{sticker}"
    return message


MAX_DOWNLOAD_MB = 2 * 1024 * 1024

async def extract_media(event, file_data, placeholder_msg = None) -> dict:
    try:
        if file_data["size"] < MAX_DOWNLOAD_MB:
            async def download_progress(current, total):
                await edit_msg(event = event, placeholder_msg = placeholder_msg, text = f"🔽🎤, 🖐️⏳...\n\n`{current//1000}kB` > `{total//1000}kB`: `{'{:.2%}'.format(current / total)}`")

            if file_data.get("file"):
                if placeholder_msg:
                    file_data["file"] = await event.client.download_media(file_data["file"], file=bytes, progress_callback = download_progress)
                else:
                    file_data["file"] = await event.client.download_media(file_data["file"], file=bytes)
                if file_data["mime"] in allowed_chat_mimetypes:
                    file_data["file"] = file_data["file"].decode("utf-8")
                    logger.debug(file_data["file"])
                return file_data
        raise Exception("Error in extract_media.")
    except Exception as e:
        logger.error(f"Error in extract_media: {str(e)}")
        return file_data

async def select_instance(chat_id = None, user_id = None, event = None):
    from bot.src.handlers.database import db
    ruid: str = ""
    if event and (not chat_id or not user_id):

        user_id = await get_id(event)
        chat_id = str(event.chat_id)
        ruid = user_id

    urClass = await db.grab_class(chat_id, user_id)


    return ruid if ruid else urClass # type: ignore
