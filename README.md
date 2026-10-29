# Odoo Construction

Construction site management on **Odoo 19 Community**, running in Docker. It tracks sites, budgets and
bills of quantities (BoQ), purchasing and subcontracts, labor, equipment and expenses, progress and billing,
change orders, daily logs and alerts, with French and Arabic translations.

This is a test project: there is no production hardening (no HTTPS, no reverse proxy).

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Compose v2), running
- Git
- On Windows, use Git Bash for the `scripts/*.sh` files
- About 4 GB of free RAM for the containers

## Quick start

### 1. Clone and configure

```bash
git clone https://github.com/MedELHattab/odoo-construction.git
cd odoo-construction

cp .env.example .env
cp config/odoo.conf.example config/odoo.conf
```

Edit both files and replace every placeholder:

| File | Setting | What to put |
| --- | --- | --- |
| `.env` | `POSTGRES_PASSWORD` | A strong database password |
| `.env` | `POSTGRES_USER`, `ODOO_DB` | Defaults (`odoo`, `construction`) are fine |
| `config/odoo.conf` | `admin_passwd` | A long random master password |

`.env` and `config/odoo.conf` are gitignored. Never commit them.

### 2. Start the stack

```bash
docker compose up -d
docker compose ps        # wait until both services are healthy
```

Odoo listens on http://localhost:8069 (bound to localhost only). The first start downloads the images.

### 3. Create the database and install the modules (first time only)

`list_db = False` hides the web database manager, so create the database from the command line.
The commands below start a second Odoo process, which is why they use port 8070 and pass the database
settings from the container environment.

In Git Bash, prefix each command with `MSYS_NO_PATHCONV=1`.

```bash
# Create the database with the base module
docker compose exec -T odoo sh -c 'odoo -d construction --db_host "$HOST" --db_user "$USER" --db_password "$PASSWORD" -i base --stop-after-init --http-port=8070'

# Install every construction addon plus the Odoo apps they rely on
MODULES=$(ls -d addons/construction_*/ | xargs -n1 basename | paste -sd, -)
docker compose exec -T odoo sh -c "odoo -d construction --db_host \"\$HOST\" --db_user \"\$USER\" --db_password \"\$PASSWORD\" -i $MODULES,sign_oca,hr_holidays,hr_attendance --stop-after-init --http-port=8070"

docker compose restart odoo
```

Open http://localhost:8069 and log in with `admin` / `admin`. **Change this password straight away**
(avatar menu, My Profile, Account Security).

### 4. Languages

French and Arabic translations ship with every addon. Enable a language under
Settings, Languages, then pick it in your user preferences.

## Everyday commands

| Task | Command |
| --- | --- |
| Start / stop | `docker compose up -d` / `docker compose down` |
| Logs | `docker compose logs -f odoo` |
| After changing Python code | `docker compose restart odoo` |
| After changing views or data | `docker compose exec odoo odoo -d construction -u <module> --stop-after-init` |

## Tests

Run every test for every `construction_*` addon in one go (needs the stack running):

```bash
bash scripts/test_all.sh
```

It upgrades all addons, runs their tests, and resets the site counter, because tests consume site codes.
Set `ODOO_API_KEY` (see below) so the counter reset can run.

To test a single module:

```bash
MSYS_NO_PATHCONV=1 docker compose exec -T odoo sh -c 'odoo -d construction --db_host "$HOST" --db_user "$USER" --db_password "$PASSWORD" -u <module> --test-tags /<module> --stop-after-init --http-port=8070'
```

## API access

`scripts/odoo_api.py` is a small client for Odoo's JSON-2 API (standard library only).

1. In Odoo: avatar menu, My Profile, Account Security, New API Key.
2. Export it in your shell. Never write it to a file:

   ```bash
   export ODOO_API_KEY=<your key>
   python scripts/odoo_api.py res.partner search_read '{"fields":["name"],"limit":5}'
   ```

Optional variables: `ODOO_URL` (default `http://localhost:8069`), `ODOO_DB` (default `construction`).

## Backups and restore

```bash
bash scripts/backup.sh
```

This writes a database dump and a filestore archive into `backups/` and keeps the 14 most recent of each.
On the original machine a Windows Task Scheduler task (`OdooConstructionBackup`) runs it daily at 13:00;
Docker Desktop must be running. The log is `backups/backup.log`.

To restore into a new database:

```bash
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" <newdb>'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d <newdb> --no-owner' < backups/<file>.dump
```

The filestore comes from `backups/filestore-<stamp>.tar.gz`; extract it into `/var/lib/odoo` in the Odoo container.

## Addons

All custom addons live in `addons/` (mounted at `/mnt/extra-addons`).

| Addon | What it does |
| --- | --- |
| `construction_site` | Sites linked to a project, budget, status workflow, chatter, roles |
| `construction_boq` | Bill of quantities, budget variance, quotation with markup |
| `construction_boq_template` | Cost categories, reusable BoQ templates, BoQ analysis pivot |
| `construction_purchase` | Purchase orders per site, subcontractor flag, committed cost vs budget |
| `construction_cost` | Site on vendor bills, actual cost, Cost Overview (list, graph, pivot) |
| `construction_labor` | Labor hours and cost from timesheets; total cost = bills + labor |
| `construction_equipment` | Equipment register, site assignments, no double-booking |
| `construction_expense` | Expenses linked to a site |
| `construction_subcontract` | Subcontract contracts and payment certificates |
| `construction_progress` | Percent complete per BoQ line, earned value, cost variance |
| `construction_billing` | Progress statements with retention; creates customer invoices |
| `construction_change_order` | Client-approved extra work that adds BoQ lines and can raise the budget |
| `construction_log` | Daily site diary: weather, workers, issues, safety incidents, photos |
| `construction_alert` | Daily cron: budget, end-date and missing-log alerts as to-dos |
| `construction_dashboard` | Kanban cards for sites, budget used %, margin to date |
| `construction_report` | Printable Site Cost Report (PDF) |
| `construction_report_log` | Latest daily logs and incidents in the PDF (auto-installs) |
| `construction_sign` | Site on signature requests, Send for Signature button |
| `construction_theme` | Brand colour and app icon |
| `sign_oca` | Third-party OCA e-signature, see [THIRD_PARTY.md](THIRD_PARTY.md) |

### Roles

Defined in `construction_site/security`: **Viewer** (read), **Site Manager** (create and edit) and
**Administrator** (delete). Project users and managers, and system admins, receive them automatically.

### Development notes

- Odoo 19 conventions: `<list>` not `<tree>`, `invisible=` expressions not `attrs`, `<chatter/>`,
  `models.Constraint`.
- `total_cost` is built from `_total_cost_amount()`. Every cost-source module extends it and must redeclare
  `_compute_total_cost` with the full `@api.depends` list (chain: labor, equipment, expense).
- Report XPath anchors must never use translatable text. Use ids such as `section_progress`.

## Translations

French (`fr`) and Arabic (`ar`) `.po` files are in each module's `i18n/` folder. They are generated from
`scripts/i18n/{fr,ar}.json` by `scripts/i18n_tools.py`.

```bash
# Export the source strings for the modules you changed
docker compose exec odoo odoo i18n export -d construction MODULES -l fr_FR ar_001

# Apply the translations
python scripts/i18n_tools.py apply fr scripts/i18n/fr.json
python scripts/i18n_tools.py apply ar scripts/i18n/ar.json

# List strings still untranslated
python scripts/i18n_tools.py missing fr scripts/i18n/fr.json
```

Add new strings to the JSON files after exporting, then apply. The Arabic wording should be reviewed by a
native speaker.

## Troubleshooting

- **Port 8069 is already in use:** stop the other service, or change the port mapping in `docker-compose.yml`.
- **Odoo cannot connect to the database:** check that `POSTGRES_PASSWORD` in `.env` has not changed since the
  database volume was created. If it has, reset with `docker compose down -v` (this deletes the data).
- **Changes to views are not visible:** upgrade the module (see Everyday commands), then hard-refresh the browser.
- **Path errors in Git Bash on Windows:** prefix the command with `MSYS_NO_PATHCONV=1`.
- **Starting over:** `docker compose down -v` removes the containers and all data, then repeat the quick start.

## Third-party code

See [THIRD_PARTY.md](THIRD_PARTY.md). `sign_oca` is licensed AGPL-3.0.
