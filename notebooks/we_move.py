import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import dash
import dash_mantine_components as dmc  # pyright: ignore[reportMissingTypeStubs]
import pandas as pd
import plotly.express as px
from dash import dcc
from pydantic import AfterValidator, BaseModel, Field, TypeAdapter
from schwifty import IBAN

# ==============================================================================
# VALIDATION HELPERS
# ==============================================================================


def validate_iban(v: str) -> str:
    try:
        IBAN(v)
    except ValueError as e:
        raise ValueError(f"Invalid IBAN: {e}") from e
    return v


# ==============================================================================
# TYPE DEFINITIONS
# ==============================================================================

IBANType = Annotated[
    str,
    AfterValidator(validate_iban),
    Field(description="International Bank Account Number"),
]
UserName = Annotated[str, Field(description="The name of the user")]


# ==============================================================================
# DATA MODELS
# ==============================================================================


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


# ==============================================================================
# DASHBOARD DATA CONTAINER
# ==============================================================================


class DashboardData(BaseModel):
    """Container for dashboard display data."""

    assets_data: list[dict[str, Any]] = Field(default_factory=list)
    liabilities_data: list[dict[str, Any]] = Field(default_factory=list)
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    net_worth: float = 0.0
    projection_df: pd.DataFrame = Field(default_factory=lambda: pd.DataFrame())

    model_config = {"arbitrary_types_allowed": True}


# ==============================================================================
# SCHEMA GENERATION
# ==============================================================================

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


# ==============================================================================
# DATA LOADING
# ==============================================================================

data_dir = root_dir / "persistent_data/data"
users_path = data_dir / "users.json"
with open(users_path) as f:
    data = json.load(f)
    if "$schema" in data:
        del data["$schema"]
    users = users_adapter.validate_python(data)


accounts_path = data_dir / "accounts.json"
with open(accounts_path) as f:
    data = json.load(f)
    if "$schema" in data:
        del data["$schema"]
    accounts = accounts_adapter.validate_python(data)


# ==============================================================================
# DATA PROCESSING
# ==============================================================================

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

# Assets table data
assets_table_data: list[dict[str, Any]] = (
    list(assets_df.to_dict("records")) if len(assets_df) > 0 else []  # type: ignore[arg-type]
)
liabilities_table_data: list[dict[str, Any]] = (
    list(liabilities_df.to_dict("records")) if len(liabilities_df) > 0 else []  # type: ignore[arg-type]
)


# ==============================================================================
# UI COMPONENTS - HEADER
# ==============================================================================


def create_header() -> Any:
    """Create the dashboard header component."""
    return dmc.Paper(
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
    )


# ==============================================================================
# UI COMPONENTS - BALANCE SHEET TAB
# ==============================================================================


def create_assets_table(table_data: list[dict[str, Any]], total: float) -> Any:
    """Create the assets table component."""
    return dmc.Paper(
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
                            for row in table_data
                        ]
                        if table_data
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
                f"Total Assets: €{total:,.2f}",
                ta="right",
                c="green",
                fw=700,
                size="xl",
                mt="md",
            ),
        ],
    )


def create_liabilities_table(table_data: list[dict[str, Any]], total: float) -> Any:
    """Create the liabilities table component."""
    return dmc.Paper(
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
                            for row in table_data
                        ]
                        if table_data
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
                f"Total Liabilities: €{total:,.2f}",
                ta="right",
                c="red",
                fw=700,
                size="xl",
                mt="md",
            ),
        ],
    )


def create_net_worth_summary(net_worth_value: float) -> Any:
    """Create the net worth summary component."""
    is_positive = net_worth_value >= 0
    color = "green" if is_positive else "red"
    return dmc.Paper(
        p="xl",
        mt="xl",
        withBorder=True,
        style={"borderColor": color},
        children=[
            dmc.Title(
                f"Net Worth: €{net_worth_value:,.2f}",
                order=1,
                ta="center",
                c=color,
            ),
        ],
    )


def create_balance_sheet_tab(data: DashboardData) -> Any:
    """Create the balance sheet tab panel content."""
    return dmc.TabsPanel(
        value="balance-sheet",
        pt="md",
        children=[
            dmc.Grid(
                gutter="xl",
                children=[
                    # Assets Column
                    dmc.GridCol(
                        span=6,
                        children=[create_assets_table(data.assets_data, data.total_assets)],
                    ),
                    # Liabilities Column
                    dmc.GridCol(
                        span=6,
                        children=[create_liabilities_table(data.liabilities_data, data.total_liabilities)],
                    ),
                ],
            ),
            # Net Worth Summary
            create_net_worth_summary(data.net_worth),
        ],
    )


# ==============================================================================
# UI COMPONENTS - PROJECTION TAB
# ==============================================================================


def create_projection_tab(projection_data: pd.DataFrame) -> Any:
    """Create the projection tab panel content."""
    return dmc.TabsPanel(
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
                            projection_data,
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
    )


# ==============================================================================
# UI COMPONENTS - TABS CONTAINER
# ==============================================================================


def create_tabs(data: DashboardData) -> Any:
    """Create the main tabs container with all tab panels."""
    return dmc.Tabs(
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
            create_balance_sheet_tab(data),
            # Tab 2: Projection
            create_projection_tab(data.projection_df),
        ],
    )


# ==============================================================================
# UI COMPONENTS - MAIN LAYOUT
# ==============================================================================


def create_layout(data: DashboardData) -> Any:
    """Create the main application layout."""
    return dmc.MantineProvider(
        forceColorScheme="dark",
        children=[
            dmc.Container(
                size="xl",
                children=[
                    # Header
                    create_header(),
                    # Main content with tabs
                    create_tabs(data),
                ],
            ),
        ],
    )


# ==============================================================================
# APPLICATION INITIALIZATION
# ==============================================================================

app = dash.Dash(__name__, external_stylesheets=dmc.styles.ALL)

# Create dashboard data container
dashboard_data = DashboardData(
    assets_data=assets_table_data,
    liabilities_data=liabilities_table_data,
    total_assets=total_assets,
    total_liabilities=total_liabilities,
    net_worth=net_worth,
    projection_df=projection_df,
)

app.layout = create_layout(dashboard_data)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
