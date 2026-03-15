"""Settings and LLM configuration sub-router.

Handles user settings, per-user overrides, and instance-wide LLM
connection configuration (API base URL, API key, model selection,
connection testing, and streaming chat proxy).
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.db.session import get_db_session
from app.services.settings import SettingsService

from ._helpers import get_settings_service

settings_router = APIRouter(tags=["settings"])


@settings_router.get("/settings")
async def settings_page(
    request: Request,
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Render the Settings page as an htmx partial."""
    from collections import defaultdict
    from app.services.llm import LLMConfigService

    templates = request.app.state.templates
    all_settings = await settings_svc.get_all_settings()
    user_overrides = await settings_svc.get_user_overrides(user.id, db)
    resolved = await settings_svc.resolve(user.id, db)

    categories = defaultdict(list)
    for s in all_settings:
        categories[s.category].append(s)

    llm_config = None
    if user.role == "owner":
        llm_svc = LLMConfigService()
        llm_config = await llm_svc.get_config(db)

    auth_service = request.app.state.auth_service
    api_tokens = await auth_service.list_api_tokens(user.id)
    webdav_endpoint = str(request.base_url).rstrip("/") + "/dav/"

<<<<<<< HEAD
    context = {
=======
    return templates.TemplateResponse(request, "browser/settings_page.html", {
>>>>>>> gsd/M002/S04
        "request": request,
        "categories": dict(categories),
        "user_overrides": user_overrides,
        "resolved": resolved,
        "all_settings": all_settings,
        "llm_config": llm_config,
        "user": user,
        "api_tokens": api_tokens,
        "webdav_endpoint": webdav_endpoint,
<<<<<<< HEAD
    }

    # htmx partial (dockview tab) vs full standalone page
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(request, "browser/settings_page.html", context)
    return templates.TemplateResponse(request, "browser/settings_standalone.html", context)
=======
    })
>>>>>>> gsd/M002/S04


@settings_router.get("/settings/data")
async def settings_data(
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Return resolved settings as JSON for the client-side cache."""
    resolved = await settings_svc.resolve(user.id, db)
    # Never expose the encrypted API key to the browser
    resolved.pop("llm.api_key", None)
    return JSONResponse(content=resolved)


@settings_router.put("/settings/{key:path}")
async def update_setting(
    key: str,
    request: Request,
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Upsert a user override. Body: {\"value\": \"...\"}"""
    body = await request.json()
    value = str(body.get("value", ""))
    await settings_svc.set_override(user.id, key, value, db)
    return JSONResponse(content={"key": key, "value": value})


@settings_router.delete("/settings/{key:path}")
async def reset_setting(
    key: str,
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a user override, reverting to default."""
    await settings_svc.reset_override(user.id, key, db)
    resolved = await settings_svc.resolve(user.id, db)
    return JSONResponse(content={"key": key, "default_value": resolved.get(key)})


# ── LLM Connection Configuration ─────────────────────────────────────────────


@settings_router.put("/llm/config")
async def save_llm_config(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Save a single LLM config field. Owner-only — instance-wide setting.
    Body: {"field": "api_base_url"|"api_key"|"default_model", "value": "..."}
    """
    from app.services.llm import LLMConfigService
    body = await request.json()
    field = body.get("field", "")
    value = str(body.get("value", ""))
    allowed = {"api_base_url", "api_key", "default_model"}
    if field in allowed:
        svc = LLMConfigService()
        kwargs: dict = {field: value}
        await svc.save_config(db, **kwargs)
    return JSONResponse(content={"ok": True})


@settings_router.post("/llm/test")
async def test_llm_connection(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Test the configured LLM connection by calling GET {base_url}/v1/models.
    Returns an HTML fragment for #llm-test-status.
    """
    import httpx
    from app.services.llm import LLMConfigService
    templates = request.app.state.templates
    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

    if not base_url:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"request": request, "status": "error", "message": "No API base URL configured."})

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/v1/models", headers=headers)
        if resp.status_code == 200:
            return templates.TemplateResponse(request, "browser/llm/test_result.html",
                {"request": request, "status": "ok", "message": "Connection successful"})
        else:
            return templates.TemplateResponse(request, "browser/llm/test_result.html",
                {"request": request, "status": "error",
                 "message": f"HTTP {resp.status_code}: {resp.text[:200]}"})
    except httpx.TimeoutException:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"request": request, "status": "error", "message": "Connection timed out after 10s"})
    except Exception as e:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"request": request, "status": "error", "message": str(e)[:200]})


@settings_router.post("/llm/models")
async def fetch_llm_models(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch available models from the configured LLM provider.
    Returns an HTML fragment that replaces #llm-model-select.
    """
    import httpx
    from app.services.llm import LLMConfigService
    templates = request.app.state.templates
    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""
    current_model = config["default_model"]

    models: list[str] = []
    error: str | None = None

    if not base_url:
        error = "No API base URL configured."
    else:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url}/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = sorted([m["id"] for m in data.get("data", [])])
            else:
                error = f"HTTP {resp.status_code}"
        except Exception as e:
            error = str(e)[:200]

    return templates.TemplateResponse(request, "browser/llm/models_select.html", {
        "request": request,
        "models": models,
        "current_model": current_model,
        "error": error,
    })


@settings_router.post("/llm/chat/stream")
async def llm_chat_stream(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """SSE streaming proxy for LLM chat completions.

    Receives JSON body: {"messages": [...], "model": "optional-override"}
    Fetches the encrypted API key from InstanceConfig, then proxies the
    streaming /v1/chat/completions response to the browser as text/event-stream.

    Accessible to any authenticated user (owner sets config; all users stream).
    """
    import httpx
    from fastapi.responses import StreamingResponse
    from app.services.llm import LLMConfigService

    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

    if not base_url:
        async def error_stream():
            yield 'data: {"error": "LLM not configured"}\n\n'
            yield "data: [DONE]\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model") or config["default_model"]

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages, "stream": True}

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n\n"
        except Exception as e:
            yield f'data: {{"error": "{str(e)[:100]}"}}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
