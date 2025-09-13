import asyncio
import contextlib
import os
from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware

from .api import router as api_router
from .dash_app import build_dash_app


def create_app() -> FastAPI:
    api = FastAPI(title="m-accounting")
    api.include_router(api_router)

    # Base URL for Dash to call back into API when deployed behind proxies
    api_base_url = os.environ.get("MACCOUNTING_API_BASE_URL", "")
    dash = build_dash_app(api_base_url=api_base_url)
    api.mount("/dash", WSGIMiddleware(dash.server))

    input_dir = os.environ.get("MACCOUNTING_INPUT_DIR", "/persistent_data/input")
    output_dir = os.environ.get("MACCOUNTING_DATA_DIR", "/persistent_data/data")

    @api.on_event("startup")
    async def _convert_on_startup() -> None:  # pragma: no cover
        async def _run() -> None:
            with contextlib.suppress(Exception):
                # Lazy import and offload to thread to avoid blocking event loop
                def _work() -> None:
                    from .convert.pdf_to_json import convert_directory

                    convert_directory(input_dir, output_dir)

                await asyncio.to_thread(_work)

        # Fire and forget; do not block startup
        asyncio.create_task(_run())

    return api


app = create_app()
