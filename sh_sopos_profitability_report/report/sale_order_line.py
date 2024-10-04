# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class ShSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sh_product_cost = fields.Float(
        string="Cost", compute="_compute_cost_product", store=True)
    sh_profit = fields.Float(
        string="Profit", compute="_compute_profit", store=True)
    order_date = fields.Datetime(
        string="Order Date", related="order_id.date_order", store=True)
    sh_return_qty = fields.Float(
        string="Return Quantity", compute="_compute_return_qty", store=True, default=0.0)
    sh_return_rate = fields.Float(
        string="Return Rate", compute="_compute_return_rate", store=True)
    sh_profitability = fields.Float(
        string="Profitability", compute="_compute_profitability", store=True)
    price_subtotal = fields.Monetary(
        compute='_compute_amount', string='Sales Value', readonly=True, store=True)
    sh_tax_amount = fields.Float(
        string="Tax Amount", compute='_compute_tax_amount', readonly=False, store=True)
    sh_tax_percentage = fields.Float(
        string="Tax Percentage", compute='_compute_tax_amount', readonly=False, store=True)
    discount = fields.Float(string='Discount (%)', default=0.0)
    sh_discount_amount = fields.Float(
        string="Discount Amount", compute='_compute_discount_amount', readonly=False, store=True)
    sh_margin = fields.Float(
        string="Margin", compute='_compute_margin', readonly=False, store=True)

    @api.depends('tax_id')
    def _compute_tax_amount(self):
        for rec in self:
            if rec.tax_id:
                tax_amount = 0.0
                tax_percentage = 0.0
                for tax in rec.tax_id:
                    tax_amount += (tax.amount * rec.price_subtotal) / 100
                    tax_percentage += tax.amount
                rec.sh_tax_amount = tax_amount
                rec.sh_tax_percentage = tax_percentage
            else:
                rec.sh_tax_amount = 0.0
                rec.sh_tax_percentage = 0.0

    @api.depends('price_subtotal')
    def _compute_discount_amount(self):
        for rec in self:
            rec.sh_discount_amount = (rec.price_subtotal * rec.discount) / 100

    @api.depends('sh_profit', 'sh_product_cost')
    def _compute_profitability(self):
        for rec in self:
            if rec.sh_product_cost > 0.0:
                rec.sh_profitability = (
                    rec.sh_profit / rec.sh_product_cost) * 100
            else:
                rec.sh_profitability = 0.0

    @api.depends('qty_delivered', 'sh_return_qty','product_uom_qty')
    def _compute_return_rate(self):
        for rec in self:
            if rec.sh_return_qty:
                if rec.qty_delivered!=0:
                    if rec.sh_return_qty > 0.0:
                        rec.sh_return_rate=rec.sh_return_qty*100/(rec.qty_delivered+rec.sh_return_qty)
                    else:
                        rec.sh_return_rate = 0.0
                else:
                    rec.sh_return_rate=100
            else:
                rec.sh_return_rate
                     
    @api.depends('qty_delivered')
    def _compute_return_qty(self):
        for rec in self:
            rec.sh_return_qty=0
            stock_picking = self.env['stock.picking'].search([])
            for picking in stock_picking:
                if picking.group_id.name == rec.order_id.name:
                    for move in picking.move_ids_without_package:
                        if move.move_dest_ids:
                            for move_line in move.move_dest_ids:
                                if move_line.product_id.id == rec.product_id.id :
                                    rec.sh_return_qty += move_line.product_uom_qty
                                else:
                                    rec.sh_return_qty += 0.0
                        else:
                            rec.sh_return_qty += 0.0
                else:
                    rec.sh_return_qty += 0.0

    @api.depends('product_id', 'product_uom_qty')
    def _compute_cost_product(self):
        for rec in self:
            rec.sh_product_cost = rec.product_id.standard_price * rec.product_uom_qty

    @api.depends('sh_product_cost', 'price_subtotal')
    def _compute_profit(self):
        for rec in self:
            rec.sh_profit = rec.price_subtotal - rec.sh_product_cost

    @api.depends('price_unit')
    def _compute_margin(self):
        for rec in self:
            rec.sh_margin = (rec.price_unit - rec.product_id.standard_price)
