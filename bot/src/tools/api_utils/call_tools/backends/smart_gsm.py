from aiohttp import ClientSession
from json import loads
from bot.src.tools.api_utils.call_tools.backends.website_view import extract_from_url
from re import search, sub

base = "https://www.smart-gsm.com/moviles"
headers = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36" 
}

async def get_device(query: str = ""):

    url = f"{base}/autocomplete/{query}"

    async with ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as resp:
                data = await resp.text()
                response_obj = loads(data)
                if not response_obj: return "Tell the user that the search failed or that phone model probably doesn't exist"

                permalink = response_obj[0].get("permalink")
                if not permalink: return "Tell the user that the search failed or that phone model probably doesn't exist"

                data = await extract_from_url(f"{base}/{permalink}")
                data = await clean_device_data(data)
                return data
        except Exception as e: raise ConnectionError(e)


async def clean_device_data(text):
    # Extraer la sección de especificaciones
    specs = search('(?s)(?<=Ficha técnica\n)(.*?|)(?=\nLee más)',text)
    name = search('(?s)(?<=\n#)(.*?)(?=\nPUBLICIDAD)', text)
    desc = search('(?s)(?<=\nComparar\n)(.*?)(?=\n\nPUBLICIDAD)', text)
    vyd = search('(?s)(?<=Ventajas y desventajas\n)(.*?|)(?=\n##  Características técnicas)', text)
    
    specs = specs.group(1).strip() if specs else "Specs not found."
    name = name.group(1).strip() if name else "Name not found."
    desc = desc.group(1).strip() if desc else "Description not found."
    vyd = vyd.group(1).strip() if desc else "Pros and cons not found."
    
    merge = f'"Name": {name}\n\n"Description": {desc}\n\n"Specifications": {specs}\n\n"Pros and Cons: {vyd}\n'
    return sub(r"[|#*-]", "", merge)