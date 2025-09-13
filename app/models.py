from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Category(BaseModel):
    id: str = Field(description="Stable category identifier")
    name: str = Field(description="Human-readable category name")
    parent_id: str | None = Field(default=None, description="Optional parent category id")


class Transaction(BaseModel):
    id: str = Field(description="Stable transaction identifier")
    date: date
    description: str = ""
    amount: float
    currency: str = Field(default="USD", min_length=3, max_length=3)
    type: Literal["expense", "income", "transfer"] = "expense"
    category_id: str | None = None
    account: str | None = None
