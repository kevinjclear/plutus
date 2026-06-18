# Deploy: plutus daily scheduler

On the `plutus` VM (see project design spec for VM/network specifics):

1. App at `/opt/plutus`; data dir per `PLUTUS_DATA_DIR`. Secrets rendered to
   an env file (chmod 600) from your secrets manager — never committed.
2. Bring up Actual: `docker compose up -d actual-server`; link institutions; copy
   `config/*.example.yaml` to `config/*.yaml` and map accounts; copy `tax_profile.example.yaml`
   to `tax_profile.yaml` and fill it in.
3. Install units: copy `deploy/plutus-daily.{service,timer}` to `/etc/systemd/system/`,
   `systemctl enable --now plutus-daily.timer`.
4. Verify: `systemctl start plutus-daily.service` once, confirm a report appears under
   `$PLUTUS_DATA_DIR/reports/` and net worth matches a known balance.

Amounts: Actual = cents (converted by the provider); SimpleFIN = decimal strings. Reports are
educational only.
