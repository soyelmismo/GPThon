from bot.src.constants import ERRFUNC, FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc
from bot.src.tools.api_utils.call_tools.backends import timezone as getTime

@openaifunc
async def what_time_is_it(timezone: str) -> str:
    """
    If the user asks for the time of any location, you will query the timezone from the city or place he requested.
    Inform the user correctly about the actual time right now.

    Args:
        timezone (str): timezone in IANA Time Zone Database format.

    Returns:
        str: Actual time in the specified timezone.
    """
    if timezone:
        try:
            return await getTime.get_current_time(timezone = timezone)
        except Exception: return ERRFUNC
    else: return FUNCNOARG
