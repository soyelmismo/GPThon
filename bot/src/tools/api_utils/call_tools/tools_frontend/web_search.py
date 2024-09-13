from bot.src.constants import ERRFUNC, FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc
from bot.src.tools.api_utils.call_tools.backends import duckduckgo
@openaifunc
async def search_on_internet(query: str, search_type: str, timelimit: str = None, max_results = 3) -> str:
    """
    Search information/recommendations and news on internet
    Reveives a search query to search information and recommendations on the web. talk freely about the results.
    Give the found sources to the user.

    Args:
        query (str): the text that will be searched
        search_type (str): use "text" or "news" depending of what the user has requested
        timelimit (str): use "d" if latest results from today, for other time limits: "w", "m", "y". Defaults to None. they are d(day), w(week), m(month), y(year).
        max_results (int): from 1 to 5 results.
    
    Returns:
        str: the search / news results to inform the user
    """

    if query:
        try:
            return await duckduckgo.search(query = query, gptcall = True, timelimit = timelimit, type = search_type, max_results=max_results)
        except Exception: return ERRFUNC
    else: return FUNCNOARG
