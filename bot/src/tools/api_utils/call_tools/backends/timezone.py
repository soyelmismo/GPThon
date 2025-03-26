from aiohttp import ClientSession
from bot.src.logs import logger
API_ENDPOINTS = [
    {"url": "https://worldtimeapi.org/api/timezone/{timezone}", "datetime_key": "datetime"},
    {"url": "https://timeapi.io/api/time/current/zone?timeZone={timezone}", "datetime_key": "dateTime"},
    # Add more fallbacks here
]

async def get_current_time(timezone):
    for api in API_ENDPOINTS:
        url = api["url"].format(timezone=timezone)
        try:
            async with ClientSession() as session:
                print(url)
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return f"The time in {timezone} is: {data[api['datetime_key']]}"
        except Exception as e:
            logger.error(f'get_current_time: {str(e)}')
    else:
        raise Exception("Time APIs didn't responded correctly.")
