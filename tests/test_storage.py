from pathlib import Path

from app.models import Category, Transaction
from app.storage import JsonStore


def test_store_roundtrip(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)

    # Categories
    c = Category(id="food", name="Food")
    store.upsert_categories([c])
    cats = store.list_categories()
    assert any(cat.id == "food" for cat in cats)

    # Transactions
    t = Transaction(id="t1", date="2024-01-01", amount=12.34, currency="USD", type="expense")
    store.upsert_transactions([t])
    txs = store.list_transactions()
    assert any(tx.id == "t1" for tx in txs)
    assert store.get_transaction("t1") is not None
    assert store.delete_transaction("t1") is True
    assert store.get_transaction("t1") is None
