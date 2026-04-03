from bot.src.logs import logger
from re import compile
from aiohttp import ClientSession
from html2text import HTML2Text

headers = {
    "User-Agent": "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/113.0 Firefox/113.0"
}
from aiohttp import ClientSession
from readability import Document
from bs4 import BeautifulSoup


async def extract_from_url(url: str) -> str:
    async with ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            html_content = await response.text()

    # Usar Readability para extraer el contenido principal
    doc = Document(html_content)
    cleaned_html = doc.summary()  # Contenido principal en HTML
    title = doc.title()  # Título del artículo

    # Opcional: Limpiar el HTML extraído y convertirlo a texto
    soup = BeautifulSoup(cleaned_html, 'html.parser')
    cleaned_text = soup.get_text(separator="\n", strip=True)

    return f"{title}\n\n{cleaned_text}"  # Devolver título y texto limpio

async def old_extract_from_url(url: str) -> str:
    
    async with ClientSession() as session:
        async with session.get(url, headers=headers, allow_redirects=True) as response:
            response.raise_for_status()
            content_length = int(response.headers.get('Content-Length', 0))
            if content_length > 1 * (1024 * 1024):
                raise ValueError("lenghtexceed")
            html_content = await response.text()

    text_maker = HTML2Text()
    text_maker.ignore_links = True
    text_maker.ignore_images = True
    text_maker.single_line_break = True
    doc = str(text_maker.handle(html_content))
    return doc

async def urls_handle(urls):
    urls_text = []
    for url in urls:
        try:
            doc = await extract_from_url(url)
            urls_text.append({"role": "user", "content": f"{url}:[\n{doc}]"})
        except ValueError as e:
            if "lenghtexceed" in str(e):
                logger.error(f'Too much size!: {e}')
            else: logger.error(f'Error: {e}')
    return urls_text

url_match = compile(r'((http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*))')

async def urls_wrapper(list_convo, prompt):
    matches = url_match.findall(prompt)
    matched_urls = []
    urls_dicts = []
    for match in matches:
        matched_urls.append(match[0])
    if matched_urls:
        urls_dicts = await urls_handle(matched_urls)

    list_convo.extend(urls_dicts)
    return list_convo