import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from .models import Category, Transaction
from .storage import JsonStore


def get_store() -> JsonStore:
    configured = os.environ.get("MACCOUNTING_DATA_DIR", "/persistent_data/data")
    root = Path(configured)
    try:
        root.mkdir(parents=True, exist_ok=True)
        return JsonStore(root)
    except Exception:
        # Fallback to workspace-local data dir if external path is not writable/available
        fallback = Path("data")
        fallback.mkdir(parents=True, exist_ok=True)
        return JsonStore(fallback)


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/transactions", response_model=list[Transaction])
def list_transactions(store: Annotated[JsonStore, Depends(get_store)]) -> list[Transaction]:
    return store.list_transactions()


@router.get("/transactions/{tx_id}", response_model=Transaction)
def get_transaction(tx_id: str, store: Annotated[JsonStore, Depends(get_store)]) -> Transaction:
    tx = store.get_transaction(tx_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return tx


@router.post("/transactions", response_model=list[Transaction])
def upsert_transactions(
    transactions: list[Transaction],
    store: Annotated[JsonStore, Depends(get_store)],
) -> list[Transaction]:
    store.upsert_transactions(transactions)
    return store.list_transactions()


@router.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: str, store: Annotated[JsonStore, Depends(get_store)]) -> dict:
    ok = store.delete_transaction(tx_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"deleted": True}


@router.get("/categories", response_model=list[Category])
def list_categories(store: Annotated[JsonStore, Depends(get_store)]) -> list[Category]:
    return store.list_categories()


@router.post("/categories", response_model=list[Category])
def upsert_categories(
    categories: list[Category],
    store: Annotated[JsonStore, Depends(get_store)],
) -> list[Category]:
    store.upsert_categories(categories)
    return store.list_categories()
