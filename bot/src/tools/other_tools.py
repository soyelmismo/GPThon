from bot.src.config import bot_prompts
import bot.src.tools.api_utils.apis_frontend as oai
from io import BytesIO
from bot.src.logs import logger
from sys import _getframe


async def get_id(event) -> str:
    return str(event.sender_id) if event.sender_id else str(event.chat_id)



role_emojis = {
    "system": "🗿",
    "user": "🥸",
    "assistant": "🤖",
    "tool": "🧰"
}

async def get_conversation(thisShit, user_id = None, summary = None):
    try:
        triggered_threshhold = 0
        tokens_threshold = 0
        previous_context_backup = ""
        previous_context_tokens = 0
        t_convo = ""
        if summary:
            thisShit.conversation.pop()
        for item in thisShit.conversation:
            role = item.get("role", " ")
            if role == "system" and thisShit.roleplaying:
                content = "*Roleplay*"
            else:
                content = item.get("content", "")
                


            if summary:
                match role:
                    case "assistant":
                        # continue
                        emoji = "You:"
                    case "user":
                        emoji = "User:"
                    case "system":
                        if not triggered_threshhold and "<context>" in content and "</context>" in content:
                            
                            emoji = "important previous notes (keep most of them):"
                            content = content.replace("<context>", "").replace("</context>", "").strip()
                            previous_context_tokens = await calculate_token_length(content)
                            tokens_threshold = thisShit.max_tokens * 0.15
                            if previous_context_tokens < tokens_threshold:
                                previous_context_backup = str(content)
                                continue
                            else:
                                triggered_threshhold = 1
                        else:
                            continue

            elif role == "tool":
                emoji = f'{emoji} [{item.get("name", "")}]' 
            else:
                emoji = role_emojis.get(role, '')



            t_convo += f"{emoji}: {content}\n\n"
        if summary:

            thisShit.conversation = [{"role": "system", "content": bot_prompts.get("summarizer", "").replace("{input}", t_convo)}]
            thisShit.temperature = 1.28
            summarized_text = await oai.quick_chat_completion(thisShit, user_id=user_id, model="llama3-8b-8192")
            if not triggered_threshhold:
                summarized_text = f'{previous_context_backup}\n{summarized_text}'.strip()
            summarized_dict = {"role": "system", "content": f'<context>\n\n{summarized_text}\n\n</context>'}
            return summarized_dict
        convo = BytesIO()
        convo.name = '🖨️.txt'
        convo.write(t_convo.encode('utf-8'))
        return convo
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")


from tiktoken import get_encoding
enc = get_encoding("cl100k_base")
async def calculate_token_length(conversation):
    total_tokens = 0
    if isinstance(conversation, list):
        for msg in conversation:
            # Calcular los tokens del contenido del mensaje
            total_tokens += len(enc.encode(msg["content"]))
            # Considerar tokens adicionales para otros campos como "role"
            total_tokens += len(enc.encode(msg["role"]))
    elif isinstance(conversation, str):
        total_tokens += len(enc.encode(conversation))
    return total_tokens
