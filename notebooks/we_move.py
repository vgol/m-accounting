# %% [markdown]
# # User Management
# This script defines the User model and handles loading/saving of user data.

# %%
import json
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, TypeAdapter
from schwifty import IBAN

# %% [markdown]
# ## Define Models
# We use Pydantic to define the User structure and a TypeAdapter for the dictionary of users.


# %%
def validate_iban(v: str) -> str:
    try:
        IBAN(v)
    except ValueError as e:
        raise ValueError(f"Invalid IBAN: {e}") from e
    return v


IBANType = Annotated[
    str, AfterValidator(validate_iban), Field(description="International Bank Account Number")
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
    shared: bool
    bank: str
    iban: IBANType
    pay_system: PaySystem
    balance: Decimal = Field(..., description="The current balance of the account")


Accounts = dict[AccountAlias, Account]
accounts_adapter = TypeAdapter(Accounts)


# %% [markdown]
# ## Generate Schema
# We generate the JSON schema for the Users model to enable validation in the JSON file.

# %%
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

# %% [markdown]
# ## Load Data
# We load the users from the JSON file, handling the removal of the `$schema` key before validation.

# %%
# Load users
data_dir = root_dir / "persistent_data/data"
users_path = data_dir / "users.json"
with open(users_path) as f:
    data = json.load(f)
    if "$schema" in data:
        del data["$schema"]
    users = users_adapter.validate_python(data)

print(users)

# Load accounts
accounts_path = data_dir / "accounts.json"
with open(accounts_path) as f:
    data = json.load(f)
    if "$schema" in data:
        del data["$schema"]
    accounts = accounts_adapter.validate_python(data)

print(accounts)

# %%
