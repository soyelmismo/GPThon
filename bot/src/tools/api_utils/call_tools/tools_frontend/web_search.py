from bot.src.constants import ERRFUNC, FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc
from bot.src.tools.api_utils.call_tools.backends import duckduckgo
@openaifunc
async def search_on_internet(query: str, search_type: str, timelimit: str = None, max_results: int = 3, region: str = "wt-wt", **kwargs) -> str:
    """
    Search information and news on internet
    User gives a sentence or word query to search information and recommendations on the web. talk freely about the results and provide the sources.
    Give the found sources to the user.

    Args:
        query (str): the keywords that will be searched
        search_type (str): can be "text", "news", "videos". depending of what the user has requested.
        timelimit (str): use "d" if latest results from today, for other time limits: "w", "m", "y". depends of what the user requested.
        max_results (int): from 1 to 5.
        region (str): wt-wt, us-en, uk-en, ru-ru, etc. MANDATORY. select the region corresponding to the language of the query.
    
    Returns:
        str: the search / news results to inform the user
    """

    if query:
        try:
            return await duckduckgo.search(query = query, timelimit = timelimit, type = search_type, max_results=max_results, region = region)
        except Exception: return ERRFUNC
    else: return FUNCNOARG
