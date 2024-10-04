# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class ProductSalesIndentReport(models.Model):
    _name = 'sh.product.sales.indent'
    _description = 'Product Sales Indent'

    name = fields.Many2one(
        comodel_name='product.product', string='Product')
    quantity = fields.Float()
    sh_customer_id = fields.Many2one(
        'res.partner', string='Customer')
    sh_category_id = fields.Many2one(
        'product.category', string='Category')
