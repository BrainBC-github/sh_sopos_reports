# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
import pytz
from datetime import timedelta
from odoo import api, models,fields
from odoo.exceptions import UserError


class CustomerSalesAnalysis(models.AbstractModel):
    _name = 'report.sh_sopos_reports.sh_cus_sale_analysis_doc'
    _description = 'Customer Sales Analysis report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        sale_order_obj = self.env["sale.order"]
        pos_order_obj = self.env["pos.order"]
        both_order_list = []
        both_product_list = []
        if data['sh_start_date']:
            date_start = fields.Datetime.from_string(data['sh_start_date'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['sh_end_date']:
            date_stop = fields.Datetime.from_string(data['sh_end_date'])
            # avoid a date_stop smaller than date_start
            if date_stop < date_start:
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
            
        if data.get('sh_partner_ids', False):
            partners = self.env['res.partner'].sudo().browse(
                data.get('sh_partner_ids', False))
        else:
            partners = self.env['res.partner'].sudo().search([])
                
        if partners:
            for partner_id in partners:
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ("partner_id", "=", partner_id.id),
                ]
                if data.get('sh_status_so') == 'all':
                    domain.append(('state', 'not in', ['cancel']))
                elif data.get('sh_status_so') == 'draft':
                    domain.append(('state', 'in', ['draft']))
                elif data.get('sh_status_so') == 'sent':
                    domain.append(('state', 'in', ['sent']))
                elif data.get('sh_status_so') == 'sale':
                    domain.append(('state', 'in', ['sale']))
                    domain.append(('locked', '=', False))
                elif data.get('sh_status_so') == 'done':
                    domain.append(('locked', '=', True))
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                search_orders = sale_order_obj.sudo().search(domain)

                if search_orders:
                    for order in search_orders:
                        if data.get('report_by') == 'order':
                            order_dic = {
                                'order_number': order.name,
                                'order_date': order.date_order,
                                'salesperson': order.user_id.name,
                                'customer_name': order.partner_id.name,
                                'salesperson_id': order.user_id.id if order.user_id else False,
                                'customer_id': order.partner_id.id,
                                'sale_amount': order.amount_total,
                                'sale_currency_id': order.currency_id.id,
                                'sale_currency_symbol': order.currency_id.symbol,  # For Excel Report
                            }
                            paid_amount = 0.0
                            if order.invoice_ids:
                                for invoice in order.invoice_ids:
                                    if invoice.move_type == 'out_invoice':
                                        paid_amount += invoice.amount_total - invoice.amount_residual
                                    elif invoice.move_type == 'out_refund':
                                        paid_amount += - \
                                            (invoice.amount_total -
                                             invoice.amount_residual)
                            order_dic.update({
                                'paid_amount': paid_amount,
                                'balance_amount': order.amount_total - paid_amount
                            })
                            order_list.append(order_dic)

                        elif data.get('report_by') == 'product' and order.order_line:
                            lines = False
                            if data.get('sh_product_ids'):
                                lines = order.order_line.sudo().filtered(
                                    lambda x: x.product_id.id in data.get('sh_product_ids'))
                            else:
                                products = self.env['product.product'].sudo().search(
                                    [])
                                lines = order.order_line.sudo().filtered(
                                    lambda x: x.product_id.id in products.ids)
                            if lines:
                                for line in lines:
                                    order_dic = {
                                        'order_number': line.order_id.name,
                                        'order_date': line.order_id.date_order,
                                        'product_name': line.product_id.name_get()[0][1],
                                        'price': line.price_unit,
                                        'qty': line.product_uom_qty,
                                        'discount': line.discount,
                                        'tax': line.price_tax,
                                        'subtotal': line.price_subtotal,
                                        'total' : line.price_subtotal + line.price_tax,
                                        'sale_currency_id': order.currency_id.id,
                                        'product_id': line.product_id.id if line.product_id else False,
                                        'sale_currency_symbol': order.currency_id.symbol,  # For Excel Report
                                    }
                                    order_list.append(order_dic)
                    for item_dic in order_list:
                        both_order_list.append(item_dic)
                    for item_dic in order_list:
                        both_product_list.append(item_dic)
            
            for partner_id in partners:
                order_list1 = []
                domain1 = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ("partner_id", "=", partner_id.id),
                ]
                if data.get('sh_status_pos') == 'all':
                    domain1.append(('state', 'not in', ['cancel']))
                elif data.get('sh_status_pos') == 'draft':
                    domain1.append(('state', 'in', ['draft']))
                elif data.get('sh_status_pos') == 'paid':
                    domain1.append(('state', 'in', ['paid']))
                elif data.get('sh_status_pos') == 'done':
                    domain1.append(('state', 'in', ['done']))
                elif data.get('sh_status_pos') == 'invoiced':
                    domain1.append(('state', 'in', ['invoiced']))
                if data.get('sh_session_id', False):
                    domain1.append(
                        ('session_id', '=', data.get('sh_session_id', False)[0]))
                else:
                    session_ids = self.env['pos.session'].sudo().search([])
                    if session_ids:
                        domain1.append(('session_id', 'in', session_ids.ids))
                if data.get('company_ids', False):
                    domain1.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                search_orders1 = pos_order_obj.sudo().search(domain1)
                if search_orders1:
                    for order in search_orders1:
                        if data.get('report_by') == 'order':
                            order_dic1 = {
                                'order_number': order.name,
                                'order_date': order.date_order,
                                'customer_name': order.partner_id.name if order.partner_id else "",
                                'salesperson': order.user_id.name,
                                'sale_amount': float("{:.2f}".format(order.amount_total)),
                                'sale_currency_id': order.currency_id.id,
                                'salesperson_id': order.user_id.id if order.user_id else False,
                                'customer_id': order.partner_id.id if order.partner_id else False,
                                'sale_currency_symbol': order.currency_id.symbol,  # For Excel Report
                            }
                            paid_amount = 0.0
                            if order.payment_ids:
                                for invoice in order.payment_ids:
                                    paid_amount = paid_amount+invoice.amount
                            order_dic1.update({
                                'paid_amount': float("{:.2f}".format(paid_amount)),
                                'balance_amount': float("{:.2f}".format(order.amount_total - paid_amount))
                            })
                            order_list1.append(order_dic1)
                        elif data.get('report_by') == 'product' and order.lines:
                            lines = False
                            if data.get('sh_product_ids'):
                                lines = order.lines.sudo().filtered(
                                    lambda x: x.product_id.id in data.get('sh_product_ids'))
                            else:
                                products = self.env['product.product'].sudo().search(
                                    [])
                                lines = order.lines.sudo().filtered(lambda x: x.product_id.id in products.ids)
                            if lines:
                                for line in lines:
                                    order_dic1 = {
                                        'order_number': line.order_id.name,
                                        'order_date': line.order_id.date_order,
                                        'product_name': line.product_id.name_get()[0][1],
                                        'price': float("{:.2f}".format(line.price_unit)),
                                        'qty': float("{:.2f}".format(line.qty)),
                                        'discount': float("{:.2f}".format(line.discount)),
                                        'tax': float("{:.2f}".format(line.price_subtotal_incl - line.price_subtotal)),
                                        'subtotal': float("{:.2f}".format(line.price_subtotal)),
                                        'total' :float("{:.2f}".format(line.price_subtotal_incl)),
                                        'sale_currency_id': order.currency_id.id,
                                        'product_id': line.product_id.id if line.product_id else False,
                                        'sale_currency_symbol': order.currency_id.symbol,  # For Excel Report
                                    }
                                    order_list1.append(order_dic1)

                    for item_dic in order_list1:
                        both_order_list.append(item_dic)
                    for item_dic in order_list1:
                        both_product_list.append(item_dic)
        
            # Without Partner POS Order
            domain_without_partner = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ("partner_id", "=", False)
                ]
            if data.get('sh_status_pos') == 'all':
                domain_without_partner.append(('state', 'not in', ['cancel']))
            elif data.get('sh_status_pos') == 'draft':
                domain_without_partner.append(('state', 'in', ['draft']))
            elif data.get('sh_status_pos') == 'paid':
                domain_without_partner.append(('state', 'in', ['paid']))
            elif data.get('sh_status_pos') == 'done':
                domain_without_partner.append(('state', 'in', ['done']))
            elif data.get('sh_status_pos') == 'invoiced':
                domain_without_partner.append(('state', 'in', ['invoiced']))
            if data.get('sh_session_id', False):
                domain_without_partner.append(
                    ('session_id', '=', data.get('sh_session_id', False)[0]))
            else:
                session_ids = self.env['pos.session'].sudo().search([])
                if session_ids:
                    domain_without_partner.append(('session_id', 'in', session_ids.ids))
            if data.get('company_ids', False):
                domain_without_partner.append(
                    ('company_id', 'in', data.get('company_ids', False)))
            without_partner_pos_order=pos_order_obj.sudo().search(domain_without_partner)
            
            if without_partner_pos_order:
                order_list1_without_partner = []
                for order in without_partner_pos_order:
                    if data.get('report_by') == 'order':
                        order_dic1 = {
                            'order_number': order.name,
                            'order_date': order.date_order,
                            'customer_name': "Walking Customer",
                            'salesperson': order.user_id.name,
                            'sale_amount': float("{:.2f}".format(order.amount_total)),
                            'sale_currency_id': order.currency_id.id,
                            'salesperson_id': order.user_id.id if order.user_id else False,
                            'customer_id': False,
                            'sale_currency_symbol': order.currency_id.symbol,  # For Excel Report
                        }
                        paid_amount = 0.0
                        if order.payment_ids:
                            for invoice in order.payment_ids:
                                paid_amount = paid_amount+invoice.amount
                        order_dic1.update({
                            'paid_amount': float("{:.2f}".format(paid_amount)),
                            'balance_amount': float("{:.2f}".format(order.amount_total - paid_amount))
                        })
                        order_list1_without_partner.append(order_dic1)
                    elif data.get('report_by') == 'product' and order.lines:
                        lines = False
                        if data.get('sh_product_ids'):
                            lines = order.lines.sudo().filtered(
                                lambda x: x.product_id.id in data.get('sh_product_ids'))
                        else:
                            products = self.env['product.product'].sudo().search(
                                [])
                            lines = order.lines.sudo().filtered(lambda x: x.product_id.id in products.ids)
                        if lines:
                            for line in lines:
                                order_dic1 = {
                                    'order_number': line.order_id.name,
                                    'order_date': line.order_id.date_order,
                                    'product_name': line.product_id.name_get()[0][1],
                                    'price': float("{:.2f}".format(line.price_unit)),
                                    'qty': float("{:.2f}".format(line.qty)),
                                    'discount': float("{:.2f}".format(line.discount)),
                                    'tax': float("{:.2f}".format(line.price_subtotal_incl - line.price_subtotal)),
                                    'subtotal': float("{:.2f}".format(line.price_subtotal)),
                                    'total' :float("{:.2f}".format(line.price_subtotal_incl)),
                                    'sale_currency_id': order.currency_id.id,
                                    'product_id': line.product_id.id if line.product_id else False,
                                    'sale_currency_symbol': order.currency_id.symbol,  # For Excel Report
                                }
                                order_list1_without_partner.append(order_dic1)
                        
                for item_dic_without_customer in order_list1_without_partner:
                        both_order_list.append(item_dic_without_customer)
                for item_dic_without_customer in order_list1_without_partner:
                        both_product_list.append(item_dic_without_customer)
            # Without Partner POS Order
            
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
        })
        
        if data.get('report_by') == 'order':
            if both_order_list:
                data.update({
                    'both_order_list': both_order_list,
                })
                return data
            else:
                raise UserError(
                    'There is no Data Found between these dates...')
        if data.get('report_by') == 'product':
            if both_product_list:
                data.update({
                    'both_product_list': both_product_list,
                })
                return data
            else:
                raise UserError(
                    'There is no Data Found between these dates...')

        data.update({
            'report_by': data.get('report_by'),
        })
        return data

