
from bot.src.constants import bot_data
from telethon.types import PeerUser

command_list = ["/ask", "/rol", "/reset", "/select", "/retry", "/stt", "/burnme"]

def is_user(event):
    if isinstance(event.message.peer_id, PeerUser):
        return True
    return False

def get_id(event) -> int:
    return event.sender_id if event.sender_id else event.chat_id

async def remove_command(conversation, event, bot_command: str = "", status: int = 0) -> str:
    longrep = f"{bot_command}@{bot_data.username}"

    message = event.message.message
    
    if message.startswith(bot_command):
        message = message.replace(longrep, "").strip()
        message = message.replace(bot_command, "").strip()

    if event.reply_to and status == 1:
        replied = await event.get_reply_message()
        replied = replied.message
        if replied.startswith(bot_command):
            replied = str(replied).replace(longrep, "").strip()
            replied = str(replied).replace(bot_command, "").strip()
        if conversation[-1]["content"] != replied:
            message = str(f"quote: {replied}\n\nuser: {message}").strip()
    return message, status


async def is_bot_mentioned(event):
    if event.message and event.message.mentioned: return True, "/ask"

    command = str(event.message.message).split(" ")[0].lower().strip()
    if "@" in command:
        command = command.split("@")[0].strip()
    try:
        media = event.message.media
        docc = bool(media and media.document)

        if is_user(event):
            if docc and not command: command = "/stt"
            if command not in command_list: command = "/ask"
            return True, command
        elif (not media and command in command_list) or (docc and command == "/stt"):
            return True, command
        else:
            return False, command

    except AttributeError:
        return True, command
