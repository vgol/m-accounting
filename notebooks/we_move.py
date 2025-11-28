import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Annotated

import dash
import dash_mantine_components as dmc  # pyright: ignore[reportMissingTypeStubs]
import pandas as pd
import plotly.express as px
from dash import dcc
from pydantic import AfterValidator, BaseModel, Field, TypeAdapter
from schwifty import IBAN


def validate_iban(v: str) -> str:
    try:
        IBAN(v)
    except ValueError as e:
        raise ValueError(f"Invalid IBAN: {e}") from e
    return v


IBANType = Annotated[
    str,
    AfterValidator(validate_iban),
    Field(description="International Bank Account Number"),
]
UserName = Annotated[str, Field(description="The name of the user")]


# Define Users related models
class User(BaseModel):
    id: int = Field(..., description="The unique identifier for the user")
    name: UserName
    email: str = Field(..., description="The email address of the user")
    full_name: str = Field(..., description="The short name of the user used as a key")


Users = dict[UserName, User]
users_adapter = TypeAdapter(Users)


class PaySystem(str, Enum):
    GIRO = "Giro"
    VISA = "Visa"
    MASTERCARD = "MasterCard"
    CASH = "Cash"  # Just cash (not a real account)


AccountAlias = Annotated[str, Field(description="The alias for the account")]


class Account(BaseModel):
    alias: AccountAlias
    owner: UserName = Field(..., description="Reference to the user who owns the account")
    users: list[UserName] = Field(default_factory=list, description="List of users with access")
    shared: bool
    bank: str
    iban: IBANType
    pay_system: PaySystem
    balance: Decimal = Field(..., description="The current balance of the account")
    timestamp: datetime = Field(default_factory=datetime.now, description="Creation or last update timestamp")


class Cash(BaseModel):
    alias: AccountAlias
    owner: UserName = Field(..., description="Reference to the user who owns the account")
    users: list[UserName] = Field(default_factory=list, description="List of users with access")
    shared: bool
    balance: Decimal = Field(..., description="The current balance of the account")
    timestamp: datetime = Field(default_factory=datetime.now, description="Creation or last update timestamp")


Accounts = dict[AccountAlias, Account | Cash]
accounts_adapter = TypeAdapter(Accounts)


# Generate schema
# Use relative path from the script location
try:
    root_dir = Path(__file__).parent.parent
except NameError:
    # Fallback for interactive execution where __file__ might not be defined
    # Assuming CWD is the workspace root
    root_dir = Path.cwd()

users_schema_path = root_dir / "schema" / "users_schema.json"
users_schema = users_adapter.json_schema()
users_schema["properties"] = {"$schema": {"type": "string"}}
with open(users_schema_path, "w") as f:
    json.dump(users_schema, f, indent=2)

accounts_schema_path = root_dir / "schema" / "accounts_schema.json"
accounts_schema = accounts_adapter.json_schema()
accounts_schema["properties"] = {"$schema": {"type": "string"}}
with open(accounts_schema_path, "w") as f:
    json.dump(accounts_schema, f, indent=2)


# Load users
data_dir = root_dir / "persistent_data/data"
users_path = data_dir / "users.json"
with open(users_path) as f:
    data = json.load(f)
    if "$schema" in data:
        del data["$schema"]
    users = users_adapter.validate_python(data)


# Load accounts
accounts_path = data_dir / "accounts.json"
with open(accounts_path) as f:
    data = json.load(f)
    if "$schema" in data:
        del data["$schema"]
    accounts = accounts_adapter.validate_python(data)


# Create a DataFrame from accounts for display
accounts_data = []
for alias, account in accounts.items():
    accounts_data.append(
        {
            "Alias": alias,
            "Owner": account.owner,
            "Shared": account.shared,
            "Balance": float(account.balance),
            "Type": "Cash" if isinstance(account, Cash) else "Bank Account",
        }
    )

accounts_df = pd.DataFrame(accounts_data)

# Assets and Liabilities DataFrames (empty scaffolds)
assets_df = pd.DataFrame(columns=["Category", "Item", "Value"])
liabilities_df = pd.DataFrame(columns=["Category", "Item", "Value"])

total_assets = assets_df["Value"].sum() if len(assets_df) > 0 else 0.0
total_liabilities = abs(liabilities_df["Value"].sum()) if len(liabilities_df) > 0 else 0.0
net_worth = total_assets - total_liabilities

# Create a simple projection from now to end of February
projection_dates = pd.date_range(start=date.today(), end=date(2026, 2, 28), freq="D")
projection_df = pd.DataFrame(
    {
        "Date": projection_dates,
        "Balance": net_worth,
    }
)

# Build the Dash app with Mantine
app = dash.Dash(__name__, external_stylesheets=dmc.styles.ALL)

# Assets table data
assets_table_data = assets_df.to_dict("records") if len(assets_df) > 0 else []
liabilities_table_data = liabilities_df.to_dict("records") if len(liabilities_df) > 0 else []

app.layout = dmc.MantineProvider(
    forceColorScheme="dark",
    children=[
        dmc.Container(
            size="xl",
            children=[
                # Header
                dmc.Paper(
                    p="xl",
                    mb="md",
                    children=[
                        dmc.Title("We Move 🏠", order=1, ta="center"),
                        dmc.Text(
                            "Move Planning Dashboard",
                            ta="center",
                            c="dimmed",
                            size="lg",
                        ),
                    ],
                ),
                # Tabs
                dmc.Tabs(
                    value="balance-sheet",
                    children=[
                        dmc.TabsList(
                            grow=True,
                            children=[
                                dmc.TabsTab("Asset / Liability Sheet", value="balance-sheet"),
                                dmc.TabsTab(
                                    "Balance Projection (Now → Feb 2026)",
                                    value="projection",
                                ),
                            ],
                        ),
                        # Tab 1: Balance Sheet
                        dmc.TabsPanel(
                            value="balance-sheet",
                            pt="md",
                            children=[
                                dmc.Grid(
                                    gutter="xl",
                                    children=[
                                        # Assets Column
                                        dmc.GridCol(
                                            span=6,
                                            children=[
                                                dmc.Paper(
                                                    p="md",
                                                    withBorder=True,
                                                    children=[
                                                        dmc.Title(
                                                            "Assets",
                                                            order=2,
                                                            c="green",
                                                            ta="center",
                                                            mb="md",
                                                        ),
                                                        dmc.Table(
                                                            striped=True,
                                                            highlightOnHover=True,
                                                            children=[
                                                                dmc.TableThead(
                                                                    dmc.TableTr(
                                                                        [
                                                                            dmc.TableTh("Category"),
                                                                            dmc.TableTh("Item"),
                                                                            dmc.TableTh(
                                                                                "Value",
                                                                                style={"textAlign": "right"},
                                                                            ),
                                                                        ]
                                                                    )
                                                                ),
                                                                dmc.TableTbody(
                                                                    [
                                                                        dmc.TableTr(
                                                                            [
                                                                                dmc.TableTd(row["Category"]),
                                                                                dmc.TableTd(row["Item"]),
                                                                                dmc.TableTd(
                                                                                    f"€{row['Value']:,.2f}",
                                                                                    style={"textAlign": "right"},
                                                                                ),
                                                                            ]
                                                                        )
                                                                        for row in assets_table_data
                                                                    ]
                                                                    if assets_table_data
                                                                    else [
                                                                        dmc.TableTr(
                                                                            [
                                                                                dmc.TableTd(
                                                                                    "No assets yet",
                                                                                    tableProps={"colSpan": 3},
                                                                                    style={
                                                                                        "textAlign": "center",
                                                                                        "color": "dimmed",
                                                                                    },
                                                                                )
                                                                            ]
                                                                        )
                                                                    ]
                                                                ),
                                                            ],
                                                        ),
                                                        dmc.Text(
                                                            f"Total Assets: €{total_assets:,.2f}",
                                                            ta="right",
                                                            c="green",
                                                            fw=700,
                                                            size="xl",
                                                            mt="md",
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        # Liabilities Column
                                        dmc.GridCol(
                                            span=6,
                                            children=[
                                                dmc.Paper(
                                                    p="md",
                                                    withBorder=True,
                                                    children=[
                                                        dmc.Title(
                                                            "Liabilities",
                                                            order=2,
                                                            c="red",
                                                            ta="center",
                                                            mb="md",
                                                        ),
                                                        dmc.Table(
                                                            striped=True,
                                                            highlightOnHover=True,
                                                            children=[
                                                                dmc.TableThead(
                                                                    dmc.TableTr(
                                                                        [
                                                                            dmc.TableTh("Category"),
                                                                            dmc.TableTh("Item"),
                                                                            dmc.TableTh(
                                                                                "Value",
                                                                                style={"textAlign": "right"},
                                                                            ),
                                                                        ]
                                                                    )
                                                                ),
                                                                dmc.TableTbody(
                                                                    [
                                                                        dmc.TableTr(
                                                                            [
                                                                                dmc.TableTd(row["Category"]),
                                                                                dmc.TableTd(row["Item"]),
                                                                                dmc.TableTd(
                                                                                    f"€{row['Value']:,.2f}",
                                                                                    style={"textAlign": "right"},
                                                                                ),
                                                                            ]
                                                                        )
                                                                        for row in liabilities_table_data
                                                                    ]
                                                                    if liabilities_table_data
                                                                    else [
                                                                        dmc.TableTr(
                                                                            [
                                                                                dmc.TableTd(
                                                                                    "No liabilities yet",
                                                                                    tableProps={"colSpan": 3},
                                                                                    style={
                                                                                        "textAlign": "center",
                                                                                        "color": "dimmed",
                                                                                    },
                                                                                )
                                                                            ]
                                                                        )
                                                                    ]
                                                                ),
                                                            ],
                                                        ),
                                                        dmc.Text(
                                                            f"Total Liabilities: €{total_liabilities:,.2f}",
                                                            ta="right",
                                                            c="red",
                                                            fw=700,
                                                            size="xl",
                                                            mt="md",
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                # Net Worth Summary
                                dmc.Paper(
                                    p="xl",
                                    mt="xl",
                                    withBorder=True,
                                    style={"borderColor": "green" if net_worth >= 0 else "red"},
                                    children=[
                                        dmc.Title(
                                            f"Net Worth: €{net_worth:,.2f}",
                                            order=1,
                                            ta="center",
                                            c="green" if net_worth >= 0 else "red",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        # Tab 2: Projection
                        dmc.TabsPanel(
                            value="projection",
                            pt="md",
                            children=[
                                dmc.Paper(
                                    p="md",
                                    withBorder=True,
                                    children=[
                                        dcc.Graph(
                                            id="balance-projection",
                                            figure=px.line(
                                                projection_df,
                                                x="Date",
                                                y="Balance",
                                                title="Projected Balance Over Time",
                                                labels={
                                                    "Balance": "Balance (€)",
                                                    "Date": "Date",
                                                },
                                                template="plotly_dark",
                                            ).update_layout(
                                                paper_bgcolor="rgba(0,0,0,0)",
                                                plot_bgcolor="rgba(0,0,0,0)",
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
