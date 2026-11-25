"""Consultas limitadas a serviços públicos fixos; dados não são instruções."""
from datetime import datetime
import html
import json
import re
from urllib.parse import urlencode, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url):
    request = Request(url, headers={'User-Agent': 'JarvisPersonalAssistant/0.8 (local personal use)'})
    with build_opener(NoRedirect).open(request, timeout=8) as response:
        data = response.read(262145)
    if len(data) > 262144: raise ValueError('Resposta excessiva')
    return json.loads(data.decode('utf8'))


def stamp():
    return datetime.now().astimezone().strftime('%d/%m/%Y %H:%M %z')


def weather():
    params = urlencode({'latitude': -3.7319, 'longitude': -38.5267, 'current': 'temperature_2m,relative_humidity_2m,wind_speed_10m', 'timezone': 'America/Fortaleza'})
    data = fetch('https://api.open-meteo.com/v1/forecast?' + params)
    current = data['current']
    return (f"Fortaleza: {current['temperature_2m']} °C, umidade {current['relative_humidity_2m']}%, "
            f"vento {current['wind_speed_10m']} km/h. Dado de {current['time']}. "
            f"Consulta: {stamp()}. Fonte: Open-Meteo https://open-meteo.com/")


def search_web(query):
    if not query.strip() or len(query) > 200: raise ValueError('Consulta inválida')
    params = urlencode({'action': 'query', 'list': 'search', 'srsearch': query, 'srlimit': 3, 'format': 'json', 'utf8': 1})
    data = fetch('https://pt.wikipedia.org/w/api.php?' + params)
    results = data.get('query', {}).get('search', [])
    lines = []
    for item in results[:3]:
        title = str(item['title'])[:150]
        snippet = html.unescape(re.sub(r'<[^>]+>', '', str(item.get('snippet', ''))))[:300]
        lines.append(f"{title}: {snippet} — https://pt.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}")
    return ('\n'.join(lines) if lines else 'Nenhum resultado encontrado.') + f'\nConsulta: {stamp()}. Fonte: Wikipédia.'
