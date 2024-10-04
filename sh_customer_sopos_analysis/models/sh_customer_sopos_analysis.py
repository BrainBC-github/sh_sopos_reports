# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class SOPOSAnalysisOrderReport(models.Model):
    _name = 'sh.customer.sopos.analysis.order'
    _description = 'Customer Analysis Order'

    name = fields.Char(string='Order Number')
    date_order = fields.Date(string='Order Date')
    salesperson_id = fields.Many2one(
        'res.users', string='Salesperson')
    sh_customer_id = fields.Many2one(
        'res.partner', string='Customer')
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id')
    sales_amount = fields.Monetary()
    amount_paid = fields.Monetary()
    balance = fields.Monetary()


class SOPOSAnalysisProductReport(models.Model):
    _name = 'sh.customer.sopos.analysis.product'
    _description = 'Customer Analysis Product'

    name = fields.Char(string='Number')
    date_order = fields.Date(string='Date')
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id')
    sh_product_id = fields.Many2one(
        comodel_name='product.product', string='Product')
    price = fields.Monetary()
    quantity = fields.Float()
    discount = fields.Float("Discount(%)")
    tax = fields.Monetary()
    subtotal = fields.Monetary()
    total = fields.Monetary()
