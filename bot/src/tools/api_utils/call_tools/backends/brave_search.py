import aiohttp
from bot.src.config import BRAVE_SEARCH_APIKEY
from bot.src.tools.api_utils.call_tools.backends.subconstants import NOQUERY, NODESC, NOTITLE, NOURL
from re import sub

SEARCH_TYPES = {
    "text": "web",
    "news": "news",
    "videos": "videos"
}

class Results():
    """Empaqueta los resultados para facilitar el manejo y formateo"""
    def __init__(self, results) -> None:
        self.results_data: list = results
        self.formatted: str = ""

async def search(
        query: str = None,
        max_results: int = 3,
        type: str = "text",
        timelimit: str = None,
        **kwargs):


    if not query: return NOQUERY
    if type not in SEARCH_TYPES: type = "text"

    url = f'https://api.search.brave.com/res/v1/{SEARCH_TYPES.get(type)}/search'
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_SEARCH_APIKEY
    }
    # if region:
    #    region = region.split("-")
    #     region = f'{region[0].lower()}-{region[1].upper()}'

    params = {
        "q": query,
        "count": max_results,
        "region": "ALL",
        "safesearch": "off"
    }
    if timelimit:
        params["freshness"] = f'p{timelimit.strip()}'
    data = {}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
            else:
                return f"Error en la solicitud: {response.status} - {response.reason}"
    results = data.get("web", data.get("results", NOQUERY))
    if isinstance(results, dict) and "results" in results:
        results = results["results"]

    data_instance = Results(results)
    await process_results(data_instance, type)
    return data_instance.formatted

async def process_results(data, type: str):
    def clean_html_tags(text: str) -> str:
        return sub(r'<[^>]+>', '', text)

    for result in data.results_data:
        title = result.get("title", NOTITLE)
        href = result.get("url", NOURL)
        body = clean_html_tags(result.get("description", NODESC))
        data.formatted += f"- {title}: {body}\nfrom: {href}\n\n"
