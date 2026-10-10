"""Civitai workflow discovery and JSON-only installation.

Workflow files are untrusted data. Never execute imported workflow content.
"""
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import folder_paths
import requests
import server
from aiohttp import web

from ...config import PLUGIN_ROOT
from ...utils.helpers import sanitize_filename
from ..utils import resolve_civitai_api_key

routes = server.PromptServer.instance.routes
SETTINGS_PATH = Path(PLUGIN_ROOT) / "workflow_settings.json"
MAX_WORKFLOW_BYTES = 8 * 1024 * 1024


def workflow_root():
    if SETTINGS_PATH.is_file():
        try:
            value = json.loads(SETTINGS_PATH.read_text(encoding="utf-8")).get("workflow_root")
            if isinstance(value, str) and os.path.isabs(value):
                return Path(value).expanduser().resolve()
        except (OSError, ValueError, TypeError):
            pass
    return (Path(folder_paths.get_user_directory()) / "default" / "workflows").resolve()


def _safe_filename(name):
    name = sanitize_filename(name or "civitai-workflow")
    stem = Path(name).stem or "civitai-workflow"
    return sanitize_filename(stem) + ".json"


def _civitai_search(query, page, limit, api_key):
    params = {"types": "Workflows", "query": query, "page": page, "limit": limit}
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    res = requests.get("https://civitai.com/api/v1/models", params=params, headers=headers, timeout=(5, 25))
    res.raise_for_status()
    return res.json()


@routes.get("/civitai/workflows/settings")
async def get_workflow_settings(request):
    return web.json_response({"workflow_root": str(workflow_root())})


@routes.post("/civitai/workflows/settings")
async def set_workflow_settings(request):
    body = await request.json()
    path = body.get("workflow_root")
    if not isinstance(path, str) or not path.strip() or not os.path.isabs(path):
        return web.json_response({"error": "An absolute workflow folder path is required"}, status=400)
    target = Path(path).expanduser().resolve()
    if not target.is_dir():
        return web.json_response({"error": "The workflow folder must already exist"}, status=400)
    if not os.access(target, os.W_OK):
        return web.json_response({"error": "The workflow folder is not writable"}, status=400)
    settings_tmp = SETTINGS_PATH.with_suffix(".json.tmp")
    try:
        settings_tmp.write_text(json.dumps({"workflow_root": str(target)}), encoding="utf-8")
        os.replace(settings_tmp, SETTINGS_PATH)
    except OSError:
        return web.json_response({"error": "Could not save workflow settings"}, status=500)
    return web.json_response({"workflow_root": str(target)})


@routes.post("/civitai/workflows/search")
async def search_workflows(request):
    body = await request.json()
    query = body.get("query", "")
    if not isinstance(query, str) or len(query) > 200:
        return web.json_response({"error": "Invalid search query"}, status=400)
    try:
        page = int(body.get("page", 1))
        limit = int(body.get("limit", 20))
    except (TypeError, ValueError):
        return web.json_response({"error": "Invalid pagination"}, status=400)
    if page < 1 or not 1 <= limit <= 100:
        return web.json_response({"error": "Invalid pagination"}, status=400)
    try:
        result = await asyncio.to_thread(_civitai_search, query, page, limit, resolve_civitai_api_key(body))
    except requests.RequestException:
        return web.json_response({"error": "Civitai workflow search unavailable"}, status=502)
    return web.json_response(result)


def _download_json_workflow(url, token):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "civitai.com" or not parsed.path.startswith("/api/download/models/"):
        raise ValueError("Only Civitai workflow download URLs are permitted")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # Do not follow redirects to arbitrary hosts with bearer credentials.
    response = requests.get(url, headers=headers, timeout=(5, 45), allow_redirects=False, stream=True)
    try:
        response.raise_for_status()
        if response.status_code in (301, 302, 303, 307, 308):
            raise ValueError("Redirected downloads are not yet supported")
        chunks = []
        size = 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > MAX_WORKFLOW_BYTES:
                raise ValueError("Workflow exceeds maximum allowed size")
            chunks.append(chunk)
        data = json.loads(b"".join(chunks).decode("utf-8"))
        if not isinstance(data, dict) or not ("nodes" in data or "prompt" in data):
            raise ValueError("Downloaded JSON does not look like a ComfyUI workflow")
        return data
    finally:
        response.close()


@routes.post("/civitai/workflows/download")
async def download_workflow(request):
    body = await request.json()
    version_id = body.get("version_id")
    if isinstance(version_id, bool) or not str(version_id).isdigit():
        return web.json_response({"error": "A numeric Civitai version ID is required"}, status=400)
    # Initial implementation: explicit download confirmation and JSON file only.
    url = f"https://civitai.com/api/download/models/{int(version_id)}"
    try:
        data = await asyncio.to_thread(_download_json_workflow, url, resolve_civitai_api_key(body))
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return web.json_response({"error": "Civitai did not return a supported workflow JSON file"}, status=422)
    except requests.RequestException:
        return web.json_response({"error": "Unable to download workflow from Civitai"}, status=502)
    root = workflow_root()
    name = _safe_filename(body.get("filename") if isinstance(body.get("filename"), str) else f"civitai-{version_id}")
    output = root / name
    try:
        root.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents overwriting existing workflows.
        with output.open("x", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
    except FileExistsError:
        return web.json_response({"error": "Workflow filename already exists"}, status=409)
    except OSError:
        return web.json_response({"error": "Could not save workflow"}, status=500)
    return web.json_response({"success": True, "filename": name, "path": str(output)})
