# Discover Civitai's current base-model catalog rather than relying solely on a
# static list. The static list remains a fallback for offline/failed requests.
import asyncio
import time

import requests
from aiohttp import web
import server

from ...config import AVAILABLE_MEILI_BASE_MODELS

prompt_server = server.PromptServer.instance

_ENUMS_URL = "https://civitai.com/api/v1/enums"
_CACHE_SECONDS = 6 * 60 * 60
_cache = {"names": None, "updated": 0.0}
_cache_lock = asyncio.Lock()


def extract_base_models(payload):
    """Extract the complete BaseModel enum, not the generation-only ActiveBaseModel."""
    if not isinstance(payload, dict):
        raise ValueError("Civitai enum response must be an object")
    raw = payload.get("BaseModel")
    if not isinstance(raw, list):
        raise ValueError("Civitai enum response has no BaseModel list")
    names = sorted({name.strip() for name in raw if isinstance(name, str) and name.strip()}, key=str.casefold)
    if not names:
        raise ValueError("Civitai returned an empty BaseModel list")
    return names


def fetch_base_models():
    response = requests.get(
        _ENUMS_URL,
        timeout=(5, 15),
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    return extract_base_models(response.json())


@prompt_server.routes.get("/civitai/base_models")
async def route_get_base_models(request):
    """Return live Civitai base models, cached with safe offline fallback."""
    now = time.monotonic()
    if _cache["names"] and now - _cache["updated"] < _CACHE_SECONDS:
        return web.json_response({"base_models": _cache["names"], "source": "cache"})
    async with _cache_lock:
        now = time.monotonic()
        if _cache["names"] and now - _cache["updated"] < _CACHE_SECONDS:
            return web.json_response({"base_models": _cache["names"], "source": "cache"})
        try:
            names = await asyncio.to_thread(fetch_base_models)
            _cache.update(names=names, updated=time.monotonic())
            return web.json_response({"base_models": names, "source": "civitai"})
        except (requests.RequestException, ValueError, TypeError) as exc:
            print(f"[Civicomfy] Base-model catalog unavailable; using fallback: {type(exc).__name__}")
            names = _cache["names"] or sorted(set(AVAILABLE_MEILI_BASE_MODELS), key=str.casefold)
            # Cache fallback only briefly to permit recovery from transient outages.
            _cache.update(names=names, updated=time.monotonic() - _CACHE_SECONDS + 60)
            return web.json_response({"base_models": names, "source": "fallback"})
