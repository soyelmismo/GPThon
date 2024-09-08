
from telethon.types import PeerUser, MessageMediaPhoto, MessageMediaDocument, DocumentAttributeFilename, DocumentAttributeVideo
from bot.src.config import (bot_data, bot_name, whitelist_chat_ids, blacklist_chat_ids, logger, command_stt, command_image,
                            command_chat
                            )
from asyncio import sleep
from telethon.errors.rpcerrorlist import MessageDeleteForbiddenError

command_list = [command_chat,
                "/rol",
                "/reset", "/select", "/retry",
                command_stt, "/burnme", "/vision",
                command_image, "/help"
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


async def quick_msg(event, text = None,  file = None, force_document = None):
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
