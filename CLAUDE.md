# Odoo Construction

Odoo 19 Community in Docker (`docker compose up -d`), http://localhost:8069, database `construction`.

- Custom addons: `addons/` (mounted at /mnt/extra-addons). After changing Python, `docker compose restart odoo`; for views/data, upgrade with `docker compose exec odoo odoo -d construction -u <module> --stop-after-init`.
- Config: `config/odoo.conf`.
- Run module install/tests (a second Odoo process, so use another port and pass the DB settings from the container env):
  `docker compose exec -T odoo sh -c 'odoo -d construction --db_host "$HOST" --db_user "$USER" --db_password "$PASSWORD" -u <module> --test-tags /<module> --stop-after-init --http-port=8070'`
  (prefix with `MSYS_NO_PATHCONV=1` in Git Bash).
- Secrets live in `.env` and `config/odoo.conf` (both gitignored; see the `.example` files). Backups: `bash scripts/backup.sh`.
- Addons: `construction_site` (sites linked to a project.project, budget, status workflow, chatter). `construction_boq` (bill of quantities, budget variance, quotation with markup). Planned next: subcontractors/purchases, cost vs budget reporting.
- Odoo 19 conventions: `<list>` not `<tree>`, `invisible=` expressions not `attrs`, `<chatter/>`, `models.Constraint`.
- API access: `python scripts/odoo_api.py <model> <method> '<json>'` (Odoo JSON-2). Needs `ODOO_API_KEY` in the environment; never write the key to a file.
- Installed apps: Sales, Invoicing, Inventory, Project, To-do. Enterprise-only apps (Accounting, MRP II, Knowledge) are not available.
