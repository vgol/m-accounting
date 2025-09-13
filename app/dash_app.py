import contextlib
import json
from typing import Any

import requests
from dash import Dash, Input, Output, State, dcc, html


def build_dash_app(api_base_url: str = "") -> Dash:
    app = Dash(__name__, requests_pathname_prefix="/dash/")

    app.layout = html.Div(
        [
            html.H2("m-accounting dashboard"),
            html.Div(
                [
                    dcc.Input(id="tx-id", placeholder="id", type="text"),
                    dcc.Input(id="tx-amount", placeholder="amount", type="number"),
                    html.Button("Add/Update", id="tx-upsert"),
                ]
            ),
            html.Pre(id="tx-list"),
            dcc.Interval(id="refresh", interval=3000, n_intervals=0),
        ]
    )

    @app.callback(Output("tx-list", "children"), Input("refresh", "n_intervals"))
    def show_transactions(_n: int) -> str:
        try:
            resp = requests.get(f"{api_base_url}/api/transactions", timeout=5)
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2)
        except Exception as exc:  # noqa: BLE001
            return f"Error: {exc}"

    @app.callback(
        Output("tx-id", "value"),
        Input("tx-upsert", "n_clicks"),
        State("tx-id", "value"),
        State("tx-amount", "value"),
        prevent_initial_call=True,
    )
    def upsert_transaction(_n: int, tx_id: str | None, amount: Any | None) -> str:
        if not tx_id or amount is None:
            return ""
        payload = [
            {
                "id": tx_id,
                "date": "2024-01-01",
                "amount": float(amount),
                "currency": "USD",
                "type": "expense",
            }
        ]
        with contextlib.suppress(Exception):
            requests.post(f"{api_base_url}/api/transactions", json=payload, timeout=5)
        return ""

    return app
