
async def get_id(event) -> str:
    return str(event.sender_id) if event.sender_id else str(event.chat_id)
