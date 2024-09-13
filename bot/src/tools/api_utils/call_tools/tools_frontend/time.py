from bot.src.constants import ERRFUNC, FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc
from bot.src.tools.api_utils.call_tools.backends import timezone as getTime

@openaifunc
async def what_time_is_it(timezone: str) -> str:
    """
    Retrieve the time.

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
