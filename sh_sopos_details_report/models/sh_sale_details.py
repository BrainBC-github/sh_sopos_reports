# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class SalesDetailsyReport(models.Model):
    _name = 'sh.sale.details'
    _description = 'Sales Details'

    name = fields.Many2one(comodel_name='product.product', string='Product')
    quantity = fields.Char()
    price_unit = fields.Char()
