from datetime import timedelta

from odoo import api, fields, models

BUDGET_LEVELS = [("none", "Within budget"), ("warning", "Near budget limit"), ("over", "Over budget")]
LEVEL_RANK = {"none": 0, "warning": 1, "over": 2}
DEFAULT_WARNING_PERCENT = 90.0


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    budget_alert_level = fields.Selection(
        BUDGET_LEVELS, default="none", readonly=True, copy=False,
        help="Highest budget alert already sent. It resets when spending falls back under the limit, "
             "so a site is alerted once per level instead of every day.",
    )
    overdue_alerted = fields.Boolean(readonly=True, copy=False)

    def write(self, vals):
        if "date_end" in vals or ("state" in vals and vals["state"] != "in_progress"):
            vals = dict(vals, overdue_alerted=False)
        return super().write(vals)

    # -- rules ----------------------------------------------------------------------------
    @api.model
    def _budget_warning_percent(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "construction_alert.budget_warning_percent", DEFAULT_WARNING_PERCENT
        )
        try:
            return float(value)
        except (TypeError, ValueError):
            return DEFAULT_WARNING_PERCENT

    def _budget_level(self):
        self.ensure_one()
        if self.budget <= 0:
            return "none"
        if self.total_cost > self.budget:
            return "over"
        if self.total_cost >= self.budget * self._budget_warning_percent() / 100.0:
            return "warning"
        return "none"

    def _previous_working_day(self, today):
        day = today - timedelta(days=1)
        while day.weekday() >= 5:  # skip Saturday and Sunday
            day -= timedelta(days=1)
        return day

    # -- delivery -------------------------------------------------------------------------
    def _notify(self, summary, note):
        """Schedule a to-do for the site manager unless the same one is still open."""
        self.ensure_one()
        if not self.manager_id:
            return False
        already_open = self.env["mail.activity"].sudo().search_count([
            ("res_model", "=", self._name), ("res_id", "=", self.id), ("summary", "=", summary),
        ])
        if already_open:
            return False
        self.activity_schedule("mail.mail_activity_data_todo", summary=summary, note=note, user_id=self.manager_id.id)
        return True

    @api.model
    def _run_alerts(self, today=None):
        """Daily check of every site in progress. Returns the number of alerts raised."""
        today = today or fields.Date.context_today(self)
        raised = 0
        for site in self.search([("state", "=", "in_progress")]):
            level = site._budget_level()
            if LEVEL_RANK[level] > LEVEL_RANK[site.budget_alert_level]:
                spent, budget = site.currency_id.format(site.total_cost), site.currency_id.format(site.budget)
                if level == "over":
                    summary = self.env._("Over budget: %s", site.display_name)
                    note = self.env._("Total cost %(spent)s exceeds the budget of %(budget)s.", spent=spent, budget=budget)
                else:
                    summary = self.env._("Budget nearly used: %s", site.display_name)
                    note = self.env._(
                        "Total cost %(spent)s has reached %(percent).0f%% of the %(budget)s budget.",
                        spent=spent, percent=site._budget_warning_percent(), budget=budget,
                    )
                raised += site._notify(summary, note)
            if level != site.budget_alert_level:
                site.budget_alert_level = level

            if site.date_end and today > site.date_end and not site.overdue_alerted:
                raised += site._notify(
                    self.env._("Past planned end date: %s", site.display_name),
                    self.env._("The planned end date was %s and the site is still in progress.", site.date_end),
                )
                site.overdue_alerted = True

            day = self._previous_working_day(today)
            started = not site.date_start or site.date_start <= day
            if started and not site.log_ids.filtered(lambda log: log.date == day):
                raised += site._notify(
                    self.env._("Missing daily log for %(day)s: %(site)s", day=day, site=site.display_name),
                    self.env._("No daily log was recorded for %s.", day),
                )
        return raised

    def action_run_alerts(self):
        raised = self._run_alerts()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Alerts checked"),
                "message": self.env._("%s new alert(s) raised.", raised),
                "type": "success",
                "sticky": False,
            },
        }
