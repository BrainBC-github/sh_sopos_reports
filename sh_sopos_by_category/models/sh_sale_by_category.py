# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class ProductSalesIndentReport(models.Model):
    _name = 'sh.sale.by.category'
    _description = 'Sales By Product Category'

    name = fields.Char(string='Number')
    date_order = fields.Date(string='Date',)
    sh_product_id = fields.Many2one(
        'product.product', string='Product')
    quantity = fields.Float()
    price = fields.Monetary()
    sh_product_uom_id = fields.Many2one(
        'uom.uom', string='UOM')
    tax = fields.Monetary()
    subtotal = fields.Monetary()
    total = fields.Monetary()
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id')
