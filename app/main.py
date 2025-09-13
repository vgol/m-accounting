from dash import Dash, dcc, html
from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware


def create_fastapi_app() -> FastAPI:
    return FastAPI(title="Marusya Accounting API")


def create_dash_app() -> Dash:
    dash_app = Dash(__name__, requests_pathname_prefix="/dash/")
    dash_app.layout = html.Div(
        [
            html.H2("m-accounting dashboard"),
            dcc.Markdown("Welcome. Add charts and controls here."),
        ]
    )
    return dash_app


def build_application() -> FastAPI:
    api = create_fastapi_app()
    dash_app = create_dash_app()
    api.mount("/dash", WSGIMiddleware(dash_app.server))
    return api


app = build_application()
