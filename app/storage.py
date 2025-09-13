import json
from collections.abc import Iterable
from pathlib import Path

from .models import Category, Transaction


class JsonStore:
    """Lightweight JSON file store for transactions and categories.

    Data layout:
      root_dir/
        transactions.json
        categories.json
    """

    def __init__(self, root_dir: Path | str) -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._tx_path = self.root / "transactions.json"
        self._cat_path = self.root / "categories.json"

        # Initialize files if missing
        if not self._tx_path.exists():
            self._write_json(self._tx_path, [])
        if not self._cat_path.exists():
            self._write_json(self._cat_path, [])

    # Utilities
    def _read_json(self, path: Path) -> list[dict]:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def _write_json(self, path: Path, data: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

    # Categories
    def list_categories(self) -> list[Category]:
        raw = self._read_json(self._cat_path)
        return [Category.model_validate(item) for item in raw]

    def upsert_categories(self, categories: Iterable[Category]) -> None:
        existing = {c.id: c for c in self.list_categories()}
        for c in categories:
            existing[c.id] = c
        self._write_json(self._cat_path, [c.model_dump() for c in existing.values()])

    # Transactions
    def list_transactions(self) -> list[Transaction]:
        raw = self._read_json(self._tx_path)
        return [Transaction.model_validate(item) for item in raw]

    def get_transaction(self, tx_id: str) -> Transaction | None:
        for tx in self.list_transactions():
            if tx.id == tx_id:
                return tx
        return None

    def upsert_transactions(self, transactions: Iterable[Transaction]) -> None:
        existing = {t.id: t for t in self.list_transactions()}
        for t in transactions:
            existing[t.id] = t
        self._write_json(self._tx_path, [t.model_dump() for t in existing.values()])

    def delete_transaction(self, tx_id: str) -> bool:
        txs = self.list_transactions()
        new_list = [t for t in txs if t.id != tx_id]
        if len(new_list) == len(txs):
            return False
        self._write_json(self._tx_path, [t.model_dump() for t in new_list])
        return True
