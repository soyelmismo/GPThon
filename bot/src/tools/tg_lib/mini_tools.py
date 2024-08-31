
from bot.src.constants import bot_data
from telethon.types import PeerUser
from telethon.types import DocumentAttributeSticker

command_list = ["/ask",
                "/rol",
                "/reset", "/select", "/retry",
                "/stt", "/burnme", "/vision",
                "/img"
                ]

async def is_user(event):
    if isinstance(event.message.peer_id, PeerUser):
        return True
    return False

async def get_id(event) -> int:
    return event.sender_id if event.sender_id else event.chat_id

async def remove_command(conversation, event, bot_command = "") -> str:
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
                    message = obj.alt

    # Elimina bot_command, bot_command@bot_data.username y @bot_data.username
    if message.startswith(bot_command) or message.startswith(bot_mention):
        message = message.replace(longrep, "").strip()
        message = message.replace(bot_command, "").strip()
        message = message.replace(bot_mention, "").strip()

    if event.reply_to:
        replied = await event.get_reply_message()


        if replied.message:
            replied = replied.message
            if replied.startswith(bot_command):
                replied = str(replied).replace(longrep, "").strip()
                replied = str(replied).replace(bot_command, "").strip()
                replied = str(replied).replace(bot_mention, "").strip()
            if str(conversation[-1]["content"]).strip() != replied and bot_command != "/img":
                message = str(f"quote: {replied}\n\nuser: {message}").strip()
            else:
                message = str(f"{replied} {message}").strip()
                
    return message


async def is_bot_mentioned(event):
    if event.message and event.message.mentioned and not str(event.message.message).startswith("/"): return True, "/ask"

    command = str(event.message.message).split(" ")[0].lower().strip()
    if "@" in command:
        command = command.split("@")[0].strip()
    try:
        media = event.message.media
        docc = bool(media and media.document)

        if await is_user(event):
            if docc and not command: command = "/stt"
            if command not in command_list: command = "/ask"
            return True, command
        elif (not media and command in command_list) or (docc and command == "/stt"):
            return True, command
        else:
            return False, command

    except AttributeError:
        return True, command
