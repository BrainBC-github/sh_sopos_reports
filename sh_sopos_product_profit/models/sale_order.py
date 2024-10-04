# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class ShSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _create_sale_order_cost(self):
        sale_orders=self.env['sale.order'].search([])
        for order in sale_orders:
            if order.order_line:
                for line in order.order_line:
                    if not line.display_type:
                        line['sh_cost']=line.product_id.standard_price