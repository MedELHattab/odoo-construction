from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.site_id:
            vals["site_id"] = self.site_id.id
        return vals
