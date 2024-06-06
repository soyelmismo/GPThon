from asyncio import create_task
from bot.src.constants import bot
from bot.src.logs import logger

channel = -1001650798623
thread = 3796


async def msg(event, text, buttons=None, parse_mode='markdown'):
    try:
        return await event.reply(message=text, buttons=buttons, link_preview=False, parse_mode=parse_mode)
    except Exception as e:
        if "Topic_deleted" in str(e): pass
        elif "Topic_closed" in str(e): pass
        else:
            logger.error(f"Exception sending a message: {e}")
            create_task(send_large_message(text, parse_mode))

#Thsi doesnt work lol, another lib yet
async def send_large_message(text, parse_mode):

    if len(text) <= 4090:
        create_task(bot.send_message(message=f'```{text}```', entity=channel, message_thread_id=thread, link_preview=False, parse_mode=parse_mode))
    else:
        # Divide el mensaje en partes más pequeñas
        message_parts = [text[i:i+4090] for i in range(0, len(text), 4090)]
        for part in message_parts:
            for _ in range(0, len(message_parts)):
                create_task(bot.send_message(message=f'```{part}```', entity=channel, message_thread_id=thread, link_preview=False, parse_mode=parse_mode))
