# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta
import pytz


class ReportSalePOSDetails(models.AbstractModel):
    _name = 'report.sh_sopos_reports.sh_sopos_detail_report'
    _description = 'sales pos details report abstract model'

    @api.model
    def get_sale_pos_details(self, date_start=False, date_stop=False, team_ids=False, company_ids=False, config_ids=False, state=False):
        """ Serialise the orders of the day information
        params: date_start, date_stop string representing the datetime of order
        """
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if date_stop:
            date_stop = fields.Datetime.from_string(date_stop)
            # avoid a date_stop smaller than date_start
            if date_stop < date_start:
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids.ids))

        if team_ids:
            domain.append(('team_id', 'in', team_ids.ids))

        if state and state == 'done':
            domain.append(('state', 'in', ['sale', 'done']))

        orders = self.env['sale.order'].sudo().search(domain)
        user_currency = self.env.company.currency_id

        total = 0.0
        products_sold = {}
        taxes = {}
        invoice_id_list = []
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency)
            else:
                total += order.amount_total
            currency = order.currency_id
            for line in order.order_line:
                if not line.display_type:
                    key = (line.product_id, line.price_unit, line.discount)
                    products_sold.setdefault(key, 0.0)
                    products_sold[key] += line.product_uom_qty

                    if line.tax_id:
                        line_taxes = line.tax_id.compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency,
                                                             line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id or False)
                        for tax in line_taxes['taxes']:
                            taxes.setdefault(
                                tax['id'], {'name': tax['name'], 'total': 0.0})
                            taxes[tax['id']]['total'] += tax['amount']

            if order.invoice_ids:
                f_invoices = order.invoice_ids.filtered(
                    lambda inv: inv.state not in ['draft', 'cancel'])
                if f_invoices:
                    invoice_id_list += f_invoices.ids

        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]

        search_journals = account_journal_obj.sudo().search([
            ('type', 'in', ['bank', 'cash'])
        ])

        journal_wise_total_payment_list = []
        if invoice_id_list and search_journals:
            for journal in search_journals:
                domain = []
                invoices = self.env['account.move'].browse(invoice_id_list)
                if invoices:
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('debit_move_id', 'in', invoices.mapped('line_ids').ids), ('credit_move_id', 'in', invoices.mapped('line_ids').ids)])
                    if reconcile_lines:
                        domain.append(('|'))
                        domain.append(
                            ('invoice_line_ids.id', 'in', reconcile_lines.mapped('credit_move_id').ids))
                        domain.append(
                            ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids))
                        domain.append(
                            ("payment_type", "in", ["inbound", "outbound"]))
                        domain.append(("journal_id", "=", journal.id))
                        domain.append(("partner_type", "in", ["customer"]))
                payments = account_payment_obj.sudo().search(domain)
                paid_total = 0.0
                if payments:
                    for payment in payments:
                        paid_total += payment.amount

                journal_wise_total_payment_list.append(
                    {"name": journal.name, "total": paid_total})
        else:
            journal_wise_total_payment_list = []
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids.ids))
        if config_ids:
            session_ids = self.env['pos.session'].sudo().search(
                [('config_id', 'in', config_ids.ids)])
            domain.append(('session_id', 'in', session_ids.ids))

        if state and state == 'done':
            domain.append(('state', 'in', ['paid', 'done', 'invoiced']))

        if team_ids:
            domain.append(('crm_team_id', 'in', team_ids.ids))

        pos_orders = self.env['pos.order'].sudo().search(domain)

        user_currency = self.env.company.currency_id
        for pos_order in pos_orders:
            if user_currency != pos_order.pricelist_id.currency_id:
                total += pos_order.pricelist_id.currency_id._convert(
                    pos_order.amount_total, user_currency)
            else:
                total += pos_order.amount_total
#             currency = order.session_id.currency_id
            currency = pos_order.currency_id
            for line in pos_order.lines:
                key = (line.product_id, line.price_unit, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.compute_all(
                        line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(
                            tax['id'], {'name': tax['name'], 'total': 0.0})
                        taxes[tax['id']]['total'] += tax['amount']

            if pos_order.account_move:
                f_invoices = pos_order.account_move.filtered(
                    lambda inv: inv.state not in ['draft', 'cancel'])
                if f_invoices:
                    invoice_id_list += f_invoices.ids

        pos_payment_obj = self.env["pos.payment"]
        pos_journal_obj = self.env["pos.payment.method"]

        search_pos_journals = pos_journal_obj.sudo().search([
        ])

        if invoice_id_list and search_pos_journals:
            for pos_journal in search_pos_journals:
                domain = [
                    ("pos_order_id.account_move", "in", invoice_id_list),
                    ("payment_method_id", "=", pos_journal.id)
                ]
                if config_ids:
                    session_ids = self.env['pos.session'].sudo().search(
                        [('config_id', 'in', config_ids.ids)])
                    domain.append(
                        ('pos_order_id.session_id', 'in', session_ids.ids))
                pos_payments = pos_payment_obj.sudo().search(domain)

                paid_total = 0.0
                if pos_payments:
                    for pos_payment in pos_payments:
                        paid_total += pos_payment.amount
                journal_wise_total_payment_list.append(
                    {"name": pos_journal.name, "total": paid_total})
        else:
            journal_wise_total_payment_list = []

        final_dic = {}
        for journal_wise_data in journal_wise_total_payment_list:
            main_total = journal_wise_data.get('total') or 0.0
            if final_dic.get(journal_wise_data.get('name'), False):
                main_total = final_dic.get(journal_wise_data.get('name'))
                main_total += journal_wise_data.get('total')
            final_dic.update({
                journal_wise_data.get('name'): main_total,
            })
        if products_sold:
            return {
                'currency_precision': user_currency.decimal_places,
                'total_paid': user_currency.round(total),
                'payments': final_dic,
                'company_name': self.env.company.name,
                'taxes': taxes.values(),
                'products': sorted([{
                    'product_id': product.id,
                    'product_name': product.name,
                    'code': product.default_code,
                    'quantity': qty,
                    'price_unit': price_unit,
                    'discount': discount,
                    'uom': product.uom_id.name
                } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
            }
        else:
            raise UserError(_(
                'There is no Data Found between these dates...'))

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        team_ids = self.env['crm.team'].browse(data['team_ids'])

        company_ids = self.env['res.company'].browse(data['company_ids'])
        if 'config_ids' in data:
            config_ids = self.env['pos.config'].browse(data['config_ids'])
        else:
            config_ids = False
        data.update(self.get_sale_pos_details(
            data['date_start'], data['date_stop'], team_ids, company_ids, config_ids, data['state']))
        return data
