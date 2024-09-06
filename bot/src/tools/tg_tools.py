
from bot.src.constants import bot_data, bot_name, bot, error_report_channel_thread, error_report_channel_id, allowed_chat_mimetypes
from telethon.types import DocumentAttributeSticker, PeerUser, MessageMediaPhoto, MessageMediaDocument, DocumentAttributeFilename
from bot.src.config import whitelist_chat_ids, blacklist_chat_ids, logger, command_stt, command_image, command_chat
from asyncio import create_task, sleep

command_list = [command_chat,
                "/rol",
                "/reset", "/select", "/retry",
                command_stt, "/burnme", "/vision",
                command_image, "/help"
                ]

max_kilobytes = 24

def check_size(size):
    return size <= max_kilobytes * 1024

async def check_media_type(event):
    try:
        file_type = ""
        mime_type = ""
        file_size = ""
        file_name = ""
        media = ""

        if event.media:
            media = event.media
        else:
            replied = await event.get_reply_message()
            logger.debug(replied)
            if replied and replied.media:
                media = replied.media
        match media:
            case MessageMediaPhoto():
                media = media.photo
                file_type = "image"
                mime_type = "jpeg"
            case MessageMediaDocument():
                media = media.document
                file_size = media.size
                file_type, mime_type = media.mime_type.split("/")
                if isinstance(media.attributes[0], DocumentAttributeFilename):
                    file_name = media.attributes[0].file_name

        return {"file": media, "type": file_type,
                "mime": mime_type, "size": file_size,
                "name": file_name}
    except Exception as e:
        logger.error(f"Error in check_media_type: {str(e)}")


async def extract_media(event, file_data, placeholder_msg = None):
    try:
        async def download_progress(current, total):
            await edit_msg(event = event, placeholder_msg = placeholder_msg, text = f'🔽🎤, 🖐️⏳...\n\n`{current//1000}kB` > `{total//1000}kB`: `{'{:.2%}'.format(current / total)}`')
            #await sleep(2)

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




async def get_id(event) -> str:
    return str(event.sender_id) if event.sender_id else str(event.chat_id)


async def remove_command(conversation, event, bot_command = "") -> str:
    message = ""
    if not isinstance(bot_command, str):
        bot_command = ""
    longrep = f"{bot_command}@{bot_data.username}"
    bot_mention = f"@{bot_data.username}"

    message = event.message.message
    msg_Attr = event.message.document.attributes if event.message.document else None
    if not message and msg_Attr:
        for obj in msg_Attr:
            match obj:
                case DocumentAttributeSticker():
                    message = f'*reacted with .webp sticker*: {obj.alt}'

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
                
    return message


async def is_bot_mentioned(event):
    try:
        message = event.message
        command = str(message.message).split(" ")[0].lower().strip()
        bot_alias = ""

        is_private_chat = isinstance(event.peer_id, PeerUser) and bool(event.chat_id == event.sender_id)

        if "@" in command:
            command, bot_alias = command.split("@")
        if (is_private_chat and command not in command_list
            or command not in command_list and bot_alias == bot_data.username
            or command == bot_name
            or message.mentioned and command not in command_list
            ):
            return True, command_chat
        elif command in command_list:
            return True, command
        else:
            return False, command

    except Exception as e:
        logger.error(f"is_bot_mentioned: {str(e)}")
        return False, command


async def whitelist_check(event):
    cd = str(event.chat_id)
    sd = str(event.sender_id)
    if ((
        whitelist_chat_ids and (
            cd not in whitelist_chat_ids
            or sd not in whitelist_chat_ids
            )
        )
        or (
        blacklist_chat_ids and (
            cd in blacklist_chat_ids
            or sd in blacklist_chat_ids
            )
        )
        ):
            await event.reply("🖕 🚫🚫🚫 🖕")
            return False

    return True


async def send_large_message(text, parse_mode='markdown'):
    try:
        if len(text) <= 4090:
            create_task(bot.send_message(message=f'```{text}```', entity=error_report_channel_id, reply_to=error_report_channel_thread, link_preview=False, parse_mode=parse_mode))
        else:
            message_parts = [text[i:i+4090] for i in range(0, len(text), 4090)]
            for part in message_parts:
                for _ in range(0, len(message_parts)):
                    create_task(bot.send_message(message=f'```{part}```', entity=error_report_channel_id, reply_to=error_report_channel_thread, link_preview=False, parse_mode=parse_mode))
    except Exception as e:
        logger.debug(str(e))
        logger.error("Error in `send_large_message`. Probably wrong channel and thread id configured.")

async def quick_msg(event, text = None, file = None, force_document = True):
        return await event.reply(text, file = file, force_document = force_document)

async def edit_msg(event, placeholder_msg, text, buttons = None):
    return await event.client.edit_message(entity = event.chat_id, message = placeholder_msg, text = text, buttons = buttons)

async def send_msg(event, text, file = None, force_document = None, delete_user_message = None, disable_delete = None):
        msg = await quick_msg(event, text, file, force_document)
        if not disable_delete:
            await sleep(5)
            await msg.delete()
        if delete_user_message:
            await event.message.delete()
        return