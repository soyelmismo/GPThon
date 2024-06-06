
from bot.src.constants import bot_data
from telethon.types import PeerUser

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
