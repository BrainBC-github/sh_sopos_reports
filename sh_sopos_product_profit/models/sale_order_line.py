# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class ShSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sh_cost = fields.Float(string='Cost')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product = self.env['product.product'].search(
                [('id', '=', vals.get('product_id'))], limit=1)
            vals['sh_cost'] = product.standard_price
        return super(ShSaleOrderLine, self).create(vals_list)
