# Odoo Construction

Odoo 19 Community in Docker (`docker compose up -d`), http://localhost:8069, database `construction`.

- Custom addons: `addons/` (mounted at /mnt/extra-addons). After changing Python, `docker compose restart odoo`; for views/data, upgrade with `docker compose exec odoo odoo -d construction -u <module> --stop-after-init`.
- Config: `config/odoo.conf`.
- API access: `python scripts/odoo_api.py <model> <method> '<json>'` (Odoo JSON-2). Needs `ODOO_API_KEY` in the environment; never write the key to a file.
- Installed apps: Sales, Invoicing, Inventory, Project, To-do. Enterprise-only apps (Accounting, MRP II, Knowledge) are not available.
