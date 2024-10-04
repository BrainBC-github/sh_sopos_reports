# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from base64 import encodebytes
from datetime import datetime
from io import BytesIO
from pytz import utc, timezone
from xlwt import Workbook, easyxf
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class SalesProductProfitWizard(models.TransientModel):
    _name = "sh.sale.product.profit.wizard"
    _description = "Sales Product Profit Wizard"

    sh_start_date = fields.Datetime(
        "Start Date", required=True, default=fields.Datetime.now)
    sh_end_date = fields.Datetime(
        "End Date", required=True, default=fields.Datetime.now)
    sh_partner_ids = fields.Many2many("res.partner", string="Customers")
    report_by = fields.Selection(
        [("customer", "Customers"), ("product", "Products"), ("both", "Both")],
        string="Report Print By",
        default="customer",
    )
    sh_session_id = fields.Many2one("pos.session", "Session")
    sh_product_ids = fields.Many2many("product.product", string="Products")
    company_ids = fields.Many2many(
        "res.company", default=lambda self: self.env.companies, string="Companies")

    @api.constrains("sh_start_date", "sh_end_date")
    def _check_dates(self):
        if self.filtered(lambda c: c.sh_end_date and c.sh_start_date > c.sh_end_date):
            raise ValidationError(_("start date must be less than end date."))

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref(
            "sh_sopos_reports.sh_sales_product_profit_action"
        ).report_action([], data=datas)

    def display_report(self):
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_sales_product_profit_doc']
        data_values_by_customer = report._get_report_values(
            docids=None, data=datas).get('both_order_by_customer')
        data_values_by_products = report._get_report_values(
            docids=None, data=datas).get('both_order_by_product')
        data_values_both_order_list = report._get_report_values(
            docids=None, data=datas).get('both_order_list')

        # Order
        if self.report_by == "customer":
            self.env['sh.sale.product.profit'].search([]).unlink()
            if data_values_by_customer:
                for order in data_values_by_customer:
                    cost = order['qty']*order['cost']
                    sale_price = order['sale_price']*order['qty']
                    profit = sale_price-cost
                    margin = (profit/sale_price)*100
                    self.env['sh.sale.product.profit'].create({
                        'sh_partner_id': order['partner_id'],
                        'name': order['order_number'],
                        'order_date': order['order_date'],
                        'product_id': order['product_id'],
                        'quantity': order['qty'],
                        'cost': cost,
                        'sale_price': sale_price,
                        'profit': profit,
                        'margin': margin,
                    })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales Product Profit',
                'view_mode': 'tree',
                'res_model': 'sh.sale.product.profit',
                'context': "{'create': False,'search_default_group_customer': 1}"

            }

        # Product
        if self.report_by == "product":
            self.env['sh.sale.product.profit'].search([]).unlink()
            if data_values_by_products:
                for order in data_values_by_products:
                    cost = order['qty']*order['cost']
                    sale_price = order['sale_price']*order['qty']
                    profit = sale_price-cost
                    margin = (profit/sale_price)*100
                    self.env['sh.sale.product.profit'].create({
                        'sh_partner_id': order['partner_id'],
                        'product_id': order['product_id'],
                        'name': order['order_number'],
                        'order_date': order['order_date'],
                        'quantity': order['qty'],
                        'cost': cost,
                        'sale_price': sale_price,
                        'profit': profit,
                        'margin': margin,
                    })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales Product Profit',
                'view_mode': 'tree',
                'res_model': 'sh.sale.product.profit',
                'context': "{'create': False,'search_default_group_product': 1}"
            }

        # Both
        if self.report_by == "both":
            self.env['sh.sale.product.profit'].search([]).unlink()
            if data_values_both_order_list:
                for order in data_values_both_order_list:
                    cost = order['cost']*order['qty']
                    sale_price = order['sale_price']*order['qty']
                    profit = sale_price - cost
                    margin = (profit/sale_price)*100
                    self.env['sh.sale.product.profit'].create({
                        'name': order['order_number'],
                        'order_date': order['order_date'],
                        'product_id': order['product_id'],
                        'sh_partner_id': order['partner_id'],
                        'quantity': order['qty'],
                        'cost': cost,
                        'sale_price': sale_price,
                        'profit': profit,
                        'margin': margin,
                    })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales Product Profit',
                'view_mode': 'tree',
                'res_model': 'sh.sale.product.profit',
                'context': "{'create': False}"
            }

    def print_xls_report(self):
        workbook = Workbook(encoding='utf-8')
        heading_format = easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Sales Product Profit', bold_center)
        left = easyxf('align: horiz center;font:bold True')
        center = easyxf('align: horiz center;')
        bold_center_total = easyxf('align: horiz center;font:bold True')

        user_tz = self.env.user.tz or utc
        local = timezone(user_tz)
        start_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.sh_start_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.sh_end_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        if self.report_by == 'customer':
            worksheet.write_merge(
                0, 1, 0, 7, 'Sales Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 7, start_date + " to " + end_date, bold)
        elif self.report_by == 'product':
            worksheet.write_merge(
                0, 1, 0, 7, 'Sales Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 7, start_date + " to " + end_date, bold)
        elif self.report_by == 'both':
            worksheet.write_merge(
                0, 1, 0, 8, 'Sales Product Profit', heading_format)
            worksheet.write_merge(
                2, 2, 0, 8, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(40 * 260)
        worksheet.col(3).width = int(
            40 * 260) if self.report_by == 'both' else int(18 * 260)
        worksheet.col(4).width = int(25 * 260)
        worksheet.col(5).width = int(25 * 260)
        worksheet.col(6).width = int(25 * 260)
        worksheet.col(7).width = int(25 * 260)

        # Get Data
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_sales_product_profit_doc']
        both_order_by_customer = report._get_report_values(
            docids=None, data=datas).get('both_order_by_customer')
        both_order_by_product = report._get_report_values(
            docids=None, data=datas).get('both_order_by_product')
        both_order_list = report._get_report_values(
            docids=None, data=datas).get('both_order_list')

        row = 2
        if self.report_by == 'customer':
            if both_order_by_customer:
                row = row+2
                total_cost = 0.0
                total_sale_price = 0.0
                total_profit = 0.0
                total_margin = 0.0
                worksheet.write(row, 0, "Order Number", bold)
                worksheet.write(row, 1, "Order Date", bold)
                worksheet.write(row, 2, "Product", bold)
                worksheet.write(row, 3, "Quantity", bold)
                worksheet.write(row, 4, "Cost", bold)
                worksheet.write(row, 5, "Sale Price", bold)
                worksheet.write(row, 6, "Profit", bold)
                worksheet.write(row, 7, "Margin(%)", bold)
                row += 1
                for rec in both_order_by_customer:
                    worksheet.write(row, 0, rec.get(
                        'order_number'), center)
                    worksheet.write(row, 1, str(
                        rec.get('order_date')), center)
                    worksheet.write(row, 2, rec.get('product'), center)
                    worksheet.write(row, 3, "{:.2f}".format(
                        rec.get('qty')), center)
                    cost = rec.get('cost', 0.0) * rec.get('qty', 0.0)
                    worksheet.write(row, 4, "{:.2f}".format(cost), center)
                    sale_price = rec.get(
                        'sale_price', 0.0) * rec.get('qty', 0.0)
                    worksheet.write(
                        row, 5, "{:.2f}".format(sale_price), center)
                    profit = rec.get('sale_price', 0.0)*rec.get('qty', 0.0) - (
                        rec.get('cost', 0.0)*rec.get('qty', 0.0))
                    worksheet.write(
                        row, 6, "{:.2f}".format(profit), center)
                    if sale_price != 0.0:
                        margin = (profit/sale_price)*100
                    else:
                        margin = 0.00
                    worksheet.write(
                        row, 7, "{:.2f}".format(margin), center)
                    total_cost = total_cost + cost
                    total_sale_price = total_sale_price + sale_price
                    if profit:
                        total_profit = total_profit + profit
                    total_margin = total_margin + margin
                    row = row + 1
                    worksheet.write(row, 3, "Total", left)
                    worksheet.write(row, 4, "{:.2f}".format(
                        total_cost), bold_center_total)
                    worksheet.write(
                        row, 5, "{:.2f}".format(
                            total_sale_price), bold_center_total)
                    worksheet.write(row, 6, "{:.2f}".format(total_profit),
                                    bold_center_total)
                    worksheet.write(row, 7, "{:.2f}".format(total_margin),
                                    bold_center_total)
                row = row + 2

        elif self.report_by == 'product':
            if both_order_by_product:
                row += 2
                total_cost = 0.0
                total_sale_price = 0.0
                total_profit = 0.0
                total_margin = 0.0
                worksheet.write(row, 0, "Order Number", bold)
                worksheet.write(row, 1, "Order Date", bold)
                worksheet.write(row, 2, "Customer", bold)
                worksheet.write(row, 3, "Quantity", bold)
                worksheet.write(row, 4, "Cost", bold)
                worksheet.write(row, 5, "Sale Price", bold)
                worksheet.write(row, 6, "Profit", bold)
                worksheet.write(row, 7, "Margin(%)", bold)
                row += 1
                for rec in both_order_by_product:
                    worksheet.write(row, 0, rec.get(
                        'order_number'), center)
                    worksheet.write(row, 1, str(
                        rec.get('order_date')), center)
                    worksheet.write(row, 2, rec.get('customer')
                                    if rec.get('customer') else '', center)
                    worksheet.write(row, 3, "{:.2f}".format(
                        rec.get('qty')), center)
                    cost = rec.get('cost', 0.0) * rec.get('qty', 0.0)
                    worksheet.write(row, 4, "{:.2f}".format(cost), center)
                    sale_price = rec.get(
                        'sale_price', 0.0) * rec.get('qty', 0.0)
                    worksheet.write(
                        row, 5, "{:.2f}".format(sale_price), center)
                    profit = rec.get('sale_price', 0.0)*rec.get('qty', 0.0) - (
                        rec.get('cost', 0.0)*rec.get('qty', 0.0))
                    worksheet.write(
                        row, 6, "{:.2f}".format(profit), center)
                    if sale_price != 0.0:
                        margin = (profit/sale_price)*100
                    else:
                        margin = 0.00
                    worksheet.write(
                        row, 7, "{:.2f}".format(margin), center)
                    total_cost = total_cost + cost
                    total_sale_price = total_sale_price + sale_price
                    if profit:
                        total_profit = total_profit + profit
                    total_margin = total_margin + margin
                    row += 1
                    worksheet.write(row, 3, "Total", left)
                    worksheet.write(row, 4, "{:.2f}".format(
                        total_cost), bold_center_total)
                    worksheet.write(
                        row, 5, "{:.2f}".format(
                            total_sale_price), bold_center_total)
                    worksheet.write(row, 6, "{:.2f}".format(total_profit),
                                    bold_center_total)
                    worksheet.write(row, 7, "{:.2f}".format(total_margin),
                                    bold_center_total)
                row += 2

        elif self.report_by == 'both':
            row += 2
            total_cost = 0.0
            total_sale_price = 0.0
            total_profit = 0.0
            total_margin = 0.0
            worksheet.write(row, 0, "Order Number", bold)
            worksheet.write(row, 1, "Order Date", bold)
            worksheet.write(row, 2, "Customer", bold)
            worksheet.write(row, 3, "Product", bold)
            worksheet.write(row, 4, "Quantity", bold)
            worksheet.write(row, 5, "Cost", bold)
            worksheet.write(row, 6, "Sale Price", bold)
            worksheet.write(row, 7, "Profit", bold)
            worksheet.write(row, 8, "Margin(%)", bold)
            row = row + 1
            if both_order_list:
                for order in both_order_list:
                    worksheet.write(row, 0, order.get(
                        'order_number'), center)
                    worksheet.write(row, 1, str(
                        order.get('order_date')), center)
                    worksheet.write(row, 2, order.get('customer')
                                    if order.get('customer') else '', center)
                    worksheet.write(row, 3, order.get('product'), center)
                    worksheet.write(row, 4, "{:.2f}".format(
                        order.get('qty')), center)
                    cost = order.get('cost', 0.0) * order.get('qty', 0.0)
                    worksheet.write(row, 5, "{:.2f}".format(cost), center)
                    sale_price = order.get(
                        'sale_price', 0.0) * order.get('qty', 0.0)
                    worksheet.write(
                        row, 6, "{:.2f}".format(sale_price), center)
                    profit = order.get('sale_price', 0.0)*order.get('qty', 0.0) - (
                        order.get('cost', 0.0)*order.get('qty', 0.0))
                    worksheet.write(
                        row, 7, "{:.2f}".format(profit), center)
                    if sale_price != 0.0:
                        margin = (profit/sale_price)*100
                    else:
                        margin = 0.00
                    worksheet.write(
                        row, 8, "{:.2f}".format(margin), center)
                    total_cost = total_cost + cost
                    total_sale_price = total_sale_price + sale_price
                    if profit:
                        total_profit = total_profit + profit
                    total_margin = total_margin + margin
                    row += 1
                    worksheet.write(row, 4, "Total", left)
                    worksheet.write(row, 5, "{:.2f}".format(
                        total_cost), bold_center_total)
                    worksheet.write(
                        row, 6, "{:.2f}".format(
                            total_sale_price), bold_center_total)
                    worksheet.write(row, 7, "{:.2f}".format(total_profit),
                                    bold_center_total)
                    worksheet.write(row, 8, "{:.2f}".format(total_margin),
                                    bold_center_total)
                row += 2

        filename = 'Sales Product Profit.xls'
        fp = BytesIO()
        workbook.save(fp)
        data = encodebytes(fp.getvalue())
        ir_attachment = self.env['ir.attachment']
        attachment_vals = {
            "name": filename,
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = ir_attachment.search([('name', '=', filename),
                                          ('type', '=', 'binary'),
                                          ('res_model', '=', 'ir.ui.view')],
                                          limit=1)
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = ir_attachment.create(attachment_vals)

        url = "/web/content/" + \
            str(attachment.id) + "?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
