"use strict";
// Read-only Actual export: connects to a self-hosted Actual server, downloads
// the budget, and writes accounts + transactions as JSON for the Python toolkit.
const fs = require("fs");
const path = require("path");
const api = require("@actual-app/api");

function env(name, fallback) {
  const v = process.env[name];
  return v === undefined || v === "" ? fallback : v;
}

async function main() {
  const dataDir = env("ACTUAL_DATA_DIR", "/work/actual");
  const outPath = env("ACTUAL_EXPORT_PATH", "/work/exports/actual-export.json");
  const startDate = env("ACTUAL_START_DATE", "2000-01-01");
  const endDate = new Date().toISOString().slice(0, 10);
  const syncId = env("ACTUAL_SYNC_ID", undefined);

  fs.mkdirSync(dataDir, { recursive: true });

  await api.init({
    dataDir,
    serverURL: env("ACTUAL_SERVER_URL", undefined),
    password: env("ACTUAL_PASSWORD", undefined),
  });
  // syncId is a POSITIONAL string arg (not a property); passing an object yields
  // "Budget [object Object] not found".
  await api.downloadBudget(syncId, { password: env("ACTUAL_BUDGET_PASSWORD", undefined) });

  const rawAccounts = await api.getAccounts();
  const cats = await api.getCategories();
  const catById = Object.fromEntries(cats.map((c) => [c.id, c.name]));
  let payeeById = {};
  if (typeof api.getPayees === "function") {
    const payees = await api.getPayees();
    payeeById = Object.fromEntries(payees.map((p) => [p.id, p.name]));
  }

  const accounts = [];
  const transactions = [];
  for (const a of rawAccounts) {
    const balance = await api.getAccountBalance(a.id); // integer cents
    if (balance === undefined || balance === null) {
      throw new Error(`getAccountBalance returned ${balance} for account id=${a.id} (${a.name}); aborting export`);
    }
    accounts.push({
      id: a.id, name: a.name,
      offbudget: !!a.offbudget, closed: !!a.closed, balance,
    });
    const txns = await api.getTransactions(a.id, startDate, endDate);
    for (const t of txns) {
      transactions.push({
        id: t.id, account: a.id, date: t.date, amount: t.amount,
        payee_name: payeeById[t.payee] || payeeById[t.payee_id] || null,
        category_name: catById[t.category] || null,
        notes: t.notes || null, cleared: !!t.cleared,
      });
    }
  }

  const out = { exported_at: new Date().toISOString(), budget_sync_id: syncId, accounts, transactions };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
  await api.shutdown();
  console.log(`wrote ${accounts.length} accounts, ${transactions.length} transactions to ${outPath}`);
}

main().catch((err) => { console.error(err); process.exit(1); });
