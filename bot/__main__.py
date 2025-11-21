from bot.src.bot import start_bot
from bot.src.logs import logger
SPRITE="""
https://github.com/soyelmismo/GPThon/tree/openai
"""

if __name__ == '__main__':
    print(SPRITE)
    logger.info("🤖 0.2.1")
    
    start_bot()
