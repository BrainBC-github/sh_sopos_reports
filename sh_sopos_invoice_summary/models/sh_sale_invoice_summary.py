# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class SalesInvoiceSummaryReport(models.Model):
    _name = 'sh.sale.invoice.summary'
    _description = 'Sales Invoice Summary'

    name = fields.Char(string='Order Number')
    date_order = fields.Date(string='Order Date')
    invoice_number = fields.Char()
    invoice_date = fields.Date()
    sh_partner_id = fields.Many2one(
        'res.partner', string='Customer')
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id')
    amount_invoiced = fields.Monetary()
    amount_paid = fields.Monetary()
    amount_due = fields.Monetary()
