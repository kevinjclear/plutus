"""SQLite storage: current-state tables, append-only history, fetch bookkeeping."""
from __future__ import annotations

import sqlite3

from plutus.model import Account, Holding, Snapshot, Transaction

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id   TEXT PRIMARY KEY,
    provider     TEXT NOT NULL,
    institution  TEXT NOT NULL,
    name         TEXT NOT NULL,
    type         TEXT NOT NULL CHECK(type IN ('checking','savings','brokerage','credit','loan','retirement')),
    tax_type     TEXT NOT NULL CHECK(tax_type IN ('taxable','traditional','roth','hsa','none')),
    currency     TEXT NOT NULL DEFAULT 'USD',
    balance      REAL NOT NULL DEFAULT 0,
    is_liability INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT
);
CREATE TABLE IF NOT EXISTS transactions (
    provider_txn_id TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES accounts(account_id),
    date            TEXT NOT NULL,
    amount          REAL NOT NULL,
    description     TEXT NOT NULL,
    category        TEXT,
    pending         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_txn_account ON transactions(account_id);
CREATE TABLE IF NOT EXISTS holdings_current (
    account_id    TEXT NOT NULL REFERENCES accounts(account_id),
    symbol        TEXT NOT NULL,
    name          TEXT,
    quantity      REAL NOT NULL,
    price         REAL NOT NULL,
    market_value  REAL NOT NULL,
    cost_basis    REAL,
    acquired_date TEXT,
    bucket        TEXT,
    as_of         TEXT NOT NULL,
    PRIMARY KEY (account_id, symbol)
);
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    taken_at          TEXT NOT NULL,
    net_worth         REAL NOT NULL,
    total_assets      REAL NOT NULL,
    total_liabilities REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshot_allocation (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(snapshot_id),
    bucket       TEXT NOT NULL,
    weight       REAL NOT NULL,
    PRIMARY KEY (snapshot_id, bucket)
);
CREATE TABLE IF NOT EXISTS fetch_runs (
    run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    provider   TEXT NOT NULL,
    started_at TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'running',
    error      TEXT
);
CREATE TABLE IF NOT EXISTS snapshot_balances (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id),
    account_id  TEXT NOT NULL,
    balance     REAL NOT NULL,
    PRIMARY KEY (snapshot_id, account_id)
);
CREATE TABLE IF NOT EXISTS snapshot_holdings (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(snapshot_id),
    account_id   TEXT NOT NULL,
    symbol       TEXT NOT NULL,
    market_value REAL NOT NULL,
    PRIMARY KEY (snapshot_id, account_id, symbol)
);
"""


class Storage:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def upsert_account(self, account: Account) -> str:
        if not account.id:
            raise ValueError("Account.id is required for storage")
        self.conn.execute(
            """
            INSERT INTO accounts (account_id, provider, institution, name, type,
                                  tax_type, currency, balance, is_liability, last_updated)
            VALUES (:id, :provider, :institution, :name, :type, :tax_type,
                    :currency, :balance, :is_liability, :last_updated)
            ON CONFLICT(account_id) DO UPDATE SET
                provider=excluded.provider, institution=excluded.institution,
                name=excluded.name, type=excluded.type, tax_type=excluded.tax_type,
                currency=excluded.currency, balance=excluded.balance,
                is_liability=excluded.is_liability, last_updated=excluded.last_updated;
            """,
            {
                "id": account.id, "provider": account.provider,
                "institution": account.institution, "name": account.name,
                "type": account.type, "tax_type": account.tax_type,
                "currency": account.currency, "balance": account.balance,
                "is_liability": 1 if account.is_liability else 0,
                "last_updated": account.last_updated,
            },
        )
        self.conn.commit()
        return account.id

    def get_accounts(self) -> list[Account]:
        rows = self.conn.execute("SELECT * FROM accounts ORDER BY institution, name;")
        return [
            Account(
                id=r["account_id"], provider=r["provider"], institution=r["institution"],
                name=r["name"], type=r["type"], tax_type=r["tax_type"],
                currency=r["currency"], balance=r["balance"],
                is_liability=bool(r["is_liability"]), last_updated=r["last_updated"],
            )
            for r in rows
        ]

    def add_transactions(self, txns: list[Transaction]) -> int:
        inserted = 0
        for t in txns:
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO transactions
                    (provider_txn_id, account_id, date, amount, description, category, pending)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (t.provider_txn_id, t.account_id, t.date, t.amount,
                 t.description, t.category, 1 if t.pending else 0),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def get_transactions(self, account_id: str | None = None) -> list[Transaction]:
        if account_id is None:
            rows = self.conn.execute("SELECT * FROM transactions ORDER BY date, provider_txn_id;")
        else:
            rows = self.conn.execute(
                "SELECT * FROM transactions WHERE account_id=? ORDER BY date, provider_txn_id;", (account_id,))
        return [
            Transaction(
                account_id=r["account_id"], date=r["date"], amount=r["amount"],
                description=r["description"], provider_txn_id=r["provider_txn_id"],
                category=r["category"], pending=bool(r["pending"]),
            )
            for r in rows
        ]

    def replace_holdings(self, account_id: str, holdings: list[Holding]) -> int:
        self.conn.execute("DELETE FROM holdings_current WHERE account_id=?;", (account_id,))
        self.conn.executemany(
            """
            INSERT INTO holdings_current
                (account_id, symbol, name, quantity, price, market_value,
                 cost_basis, acquired_date, bucket, as_of)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            [(h.account_id, h.symbol, h.name, h.quantity, h.price, h.market_value,
              h.cost_basis, h.acquired_date, h.bucket, h.as_of) for h in holdings],
        )
        self.conn.commit()
        return len(holdings)

    def get_holdings(self, account_id: str | None = None) -> list[Holding]:
        if account_id is None:
            rows = self.conn.execute("SELECT * FROM holdings_current ORDER BY account_id, symbol;")
        else:
            rows = self.conn.execute(
                "SELECT * FROM holdings_current WHERE account_id=? ORDER BY symbol;", (account_id,))
        return [
            Holding(
                account_id=r["account_id"], symbol=r["symbol"], name=r["name"],
                quantity=r["quantity"], price=r["price"], market_value=r["market_value"],
                cost_basis=r["cost_basis"], acquired_date=r["acquired_date"],
                bucket=r["bucket"], as_of=r["as_of"],
            )
            for r in rows
        ]

    def write_snapshot(self, snapshot: Snapshot, allocation: dict[str, float]) -> int:
        cur = self.conn.execute(
            """INSERT INTO snapshots (taken_at, net_worth, total_assets, total_liabilities)
               VALUES (?, ?, ?, ?);""",
            (snapshot.taken_at, snapshot.net_worth, snapshot.total_assets,
             snapshot.total_liabilities),
        )
        sid = cur.lastrowid
        self.conn.executemany(
            "INSERT INTO snapshot_allocation (snapshot_id, bucket, weight) VALUES (?, ?, ?);",
            [(sid, bucket, weight) for bucket, weight in allocation.items()],
        )
        self.conn.commit()
        return sid

    def get_snapshots(self) -> list[Snapshot]:
        rows = self.conn.execute("SELECT * FROM snapshots ORDER BY taken_at;")
        return [
            Snapshot(taken_at=r["taken_at"], net_worth=r["net_worth"],
                     total_assets=r["total_assets"], total_liabilities=r["total_liabilities"])
            for r in rows
        ]

    def start_fetch_run(self, provider: str, started_at: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO fetch_runs (provider, started_at) VALUES (?, ?);",
            (provider, started_at))
        self.conn.commit()
        return cur.lastrowid

    def finish_fetch_run(self, run_id: int, status: str, error: str | None = None) -> None:
        self.conn.execute(
            "UPDATE fetch_runs SET status=?, error=? WHERE run_id=?;", (status, error, run_id))
        self.conn.commit()

    def add_snapshot_detail(self, snapshot_id: int, accounts, holdings) -> None:
        self.conn.executemany(
            "INSERT INTO snapshot_balances (snapshot_id, account_id, balance) VALUES (?, ?, ?);",
            [(snapshot_id, a.id, a.balance) for a in accounts])
        self.conn.executemany(
            "INSERT INTO snapshot_holdings (snapshot_id, account_id, symbol, market_value) VALUES (?, ?, ?, ?);",
            [(snapshot_id, h.account_id, h.symbol, h.market_value) for h in holdings])
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
