
from telethon.types import MessageMediaPhoto, MessageMediaDocument, DocumentAttributeFilename, DocumentAttributeVideo, DocumentAttributeSticker
import bot.src.config as c
from bot.src.logs import logger
from asyncio import sleep, CancelledError
from telethon.errors.rpcerrorlist import MessageDeleteForbiddenError
from io import BytesIO
from re import search, sub


command_list = [c.command_chat,
                "/rol",
                "/reset", "/select", "/retry",
                c.command_stt, "/burnme", "/vision",
                c.command_image, "/help", "/embed",
                "/tts"
                ]

async def check_media_type(event) -> dict:
    file_data = {"file": any, "type": "",
                "mime": "", "size": 0,
                "name": ""}
    try:

        media = ""

        if event.media:
            media = event.media
        else:
            replied = await event.get_reply_message()
            logger.debug(replied)
            if replied and replied.media:
                media = replied.media
        if media:
            match media:
                case MessageMediaPhoto():
                    media = media.photo
                    file_data["type"] = "image"
                    file_data["mime"] = "jpeg"
                case MessageMediaDocument():
                    media = media.document
                    file_data["size"] = media.size # type: ignore
                    file_data["type"], file_data["mime"] = media.mime_type.split("/") # type: ignore
                    for instance_type in media.attributes:
                        if isinstance(instance_type, DocumentAttributeVideo):
                            if instance_type.duration < 15:
                                file_data["type"] = "image"
                        if isinstance(instance_type, DocumentAttributeFilename): # type: ignore
                            file_data["name"] = instance_type.file_name # type: ignore
            file_data["file"] = media

    except Exception as e:
        logger.error(f"Error in check_media_type: {str(e)}")
    finally:
        return file_data

async def is_bot_mentioned(event):
    try:
        message = event.message
        command = str(message.message).split(" ")[0].split("\n")[0].lower().strip()
        command = sub(r'[^\w]+$','', command)
        bot_alias = ""

        audio = (event.message.document and event.message.document.mime_type.startswith("audio"))
        if "@" in command:
            command, bot_alias = command.split("@")
        if (not audio and (event.is_private and command not in command_list
            or command not in command_list and bot_alias == c.bot_data.username
            or command == c.bot_name
            or message.mentioned and command not in command_list)
            ):
            return True, c.command_chat
        elif command in command_list:
            return True, command
        elif audio:
            return True, c.command_transcribe
        else:
            return False, command

    except Exception as e:
        logger.error(f"is_bot_mentioned: {str(e)}")
        return False, command

async def whitelist_check(event):
    cd = str(event.chat_id)
    sd = str(event.sender_id)
    if ((
        c.whitelist_chat_ids and (
            cd not in c.whitelist_chat_ids
            or sd not in c.whitelist_chat_ids
            )
        )
        or (
        c.blacklist_chat_ids and (
            cd in c.blacklist_chat_ids
            or sd in c.blacklist_chat_ids
            )
        )
        ):
            await event.reply("🖕 🚫🚫🚫 🖕")
            return False

    return True


async def quick_msg(event, text = None,  file = None, force_document = None):
    if file and isinstance(file, BytesIO):
        file.seek(0)
    return await event.reply(text, file = file, force_document = force_document)

async def send_msg(event, text, file = None, force_document = None, delete_user_message = None, disable_delete = None):
    msg = await quick_msg(event, text, file, force_document)
    if not disable_delete or delete_user_message:
        await sleep(5)
        if not disable_delete:
            await msg.delete()
        if delete_user_message:
            try:
                await event.message.delete()
            except MessageDeleteForbiddenError:
                pass
    return


async def edit_msg(event, placeholder_msg, text, buttons = None):
    return await event.client.edit_message(entity = event.chat_id, message = placeholder_msg, text = text, buttons = buttons)


async def remove_command(conversation, event, bot_command = "") -> str:
    

    message = ""
    if not isinstance(bot_command, str):
        bot_command = ""
    longrep = f"{bot_command}@{c.bot_data.username}"
    bot_mention = f"@{c.bot_data.username}"

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
                sticker = f'\n*sent {mime} '
                
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
            if "✍️" in replied and "👗" in replied:
                replied = search('(?s)(?=[^✍️ ])(.*?)(?=\n👗)', replied)
                replied = replied.group(1).strip()
            if replied.startswith(bot_command):
                replied = str(replied).replace(longrep, "").strip()
                replied = str(replied).replace(bot_command, "").strip()
                replied = str(replied).replace(bot_mention, "").strip()
            if bot_command in [c.command_image, "/select", "/embed"]:
                message = str(f"{replied} {message}").strip()
            elif replied and (
                str(conversation[-1]["content"]).strip() if len(conversation)
                else "") != replied:
                message = str(f"\n> {replied}\n\n{message}")
            
    if sticker:
        message = f"{message}{sticker}"
    return message


MAX_DOWNLOAD_MB = 25 * 1024 * 1024

async def extract_media(event, file_data, placeholder_msg = None, buttons = None) -> dict:
    try:
        if file_data["size"] < MAX_DOWNLOAD_MB:
            async def download_progress(current, total):
                await edit_msg(event = event, placeholder_msg = placeholder_msg, text = f"🔽🎤, 🖐️⏳...\n\n`{current//1000}kB` > `{total//1000}kB`: `{'{:.2%}'.format(current / total)}`", buttons=buttons)

            if file_data.get("file"):
                if placeholder_msg:
                    file_data["file"] = await event.client.download_media(file_data["file"], file=bytes, progress_callback = download_progress)
                else:
                    file_data["file"] = await event.client.download_media(file_data["file"], file=bytes)
                if file_data["mime"] in c.allowed_chat_mimetypes:
                    file_data["file"] = file_data["file"].decode("utf-8")
                    logger.debug(file_data["file"])
                return file_data
        else:
            raise FileNotFoundError("File is too big.")
    except CancelledError as e:
        if "Cancelled by user." in str(e):
            return "Task_cancellled"
    except Exception as e:
        logger.error(f"Error in extract_media: {str(e)}")
        return file_data



async def select_instance(chat_id = None, user_id = None, event = None, task_id = None):
    from bot.src.handlers import database as rdb

    if event and task_id:
        if task_id.endswith("✦"):
            return str(event.chat_id)
        return await get_id(event)

    return await rdb.db.grab_class(chat_id, user_id)

async def get_id(event) -> str:
    return str(event.sender_id) if event.sender_id else str(event.chat_id)
