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


class SalesAnalysisWizard(models.TransientModel):
    _name = "sh.sale.analysis.wizard"
    _description = "Sales Analysis Wizard"

    sh_start_date = fields.Datetime(
        "Start Date", required=True, default=fields.Datetime.now)
    sh_end_date = fields.Datetime(
        "End Date", required=True, default=fields.Datetime.now)
    sh_partner_ids = fields.Many2many("res.partner", string="Customers")
    sh_status_so = fields.Selection(
        [
            ("all", "All"),
            ("draft", "Draft"),
            ("sent", "Quotation Sent"),
            ("sale", "Sales Order"),
            ("done", "Locked"),
        ],
        string="Status ( SO )",
        default="all",
    )
    sh_status_pos = fields.Selection(
        [
            ("all", "All"),
            ("draft", "Draft"),
            ("paid", "Paid"),
            ("done", "Posted"),
            ("invoiced", "Invoiced"),
        ],
        string="Status ( POS )",
        default="all",
    )
    report_by = fields.Selection(
        [("order", "Sales Order"), ("product", "Products")],
        string="Report Print By",
        default="order",
    )
    sh_product_ids = fields.Many2many("product.product", string="Products")
    sh_session_id = fields.Many2one("pos.session", "Session")
    company_ids = fields.Many2many(
        "res.company", default=lambda self: self.env.companies, string="Companies"
    )

    @api.constrains("sh_start_date", "sh_end_date")
    def _check_dates(self):
        if self.filtered(lambda c: c.sh_end_date and c.sh_start_date > c.sh_end_date):
            raise ValidationError(_("start date must be less than end date."))

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref(
            "sh_sopos_reports.sh_cus_sales_analysis_action"
        ).report_action([], data=datas)

    def display_report(self):
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_cus_sale_analysis_doc']
        order_data_values = report._get_report_values(
            docids=None, data=datas).get('both_order_list')
        product_data_values = report._get_report_values(
            docids=None, data=datas).get('both_product_list')

        # Order
        if self.report_by == "order":
            self.env['sh.customer.sopos.analysis.order'].search([]).unlink()
            if order_data_values:
                for order in order_data_values:
                    self.env['sh.customer.sopos.analysis.order'].create({
                        'sh_customer_id': order['customer_id'],
                        'name': order['order_number'],
                        'date_order': order['order_date'],
                        'salesperson_id': order['salesperson_id'],
                        'sales_amount': order['sale_amount'],
                        'amount_paid': order['paid_amount'],
                        'balance': order['balance_amount']
                    })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Customer Sales/Pos Analysis',
                'view_mode': 'tree',
                'res_model': 'sh.customer.sopos.analysis.order',
                'context': "{'create': False}"
            }

        # Product
        if self.report_by == "product":
            self.env['sh.customer.sopos.analysis.product'].search([]).unlink()
            if product_data_values:
                for order in product_data_values:
                    self.env['sh.customer.sopos.analysis.product'].create({
                        'name': order['order_number'],
                        'date_order': order['order_date'],
                        'sh_product_id': order['product_id'],
                        'price': order['price'],
                        'quantity': order['qty'],
                        'discount': order['discount'],
                        'tax': order['tax'],
                        'subtotal': order['subtotal'],
                        'total': order['total']
                    })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Customer Sales/Pos Analysis',
                'view_mode': 'tree',
                'res_model': 'sh.customer.sopos.analysis.product',
                'context': "{'create': False}"
            }

    def print_xls_report(self):
        workbook = Workbook(encoding="utf-8")
        heading_format = easyxf(
            "font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center"
        )
        bold = easyxf(
            "font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center"
        )
        bold_center = easyxf(
            "font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;"
        )
        worksheet = workbook.add_sheet("Customer Sales Analysis", bold_center)
        left = easyxf("align: horiz center;font:bold True")
        center = easyxf("align: horiz center;")
        bold_center_total = easyxf("align: horiz center;font:bold True")

        user_tz = self.env.user.tz or utc
        local = timezone(user_tz)
        start_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.sh_start_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.sh_end_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        if self.report_by == 'order':
            worksheet.write_merge(
                0, 1, 0, 6, 'Customer Sales Analysis', heading_format)
            worksheet.write_merge(
                2, 2, 0, 6, start_date + " to " + end_date, bold)
        elif self.report_by == 'product':
            worksheet.write_merge(
                0, 1, 0, 8, 'Customer Sales Analysis', heading_format)
            worksheet.write_merge(
                2, 2, 0, 8, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(
            30 * 260) if self.report_by == 'order' else int(40 * 260)
        worksheet.col(3).width = int(25 * 260)
        worksheet.col(4).width = int(25 * 260)
        worksheet.col(5).width = int(25 * 260)
        worksheet.col(6).width = int(25 * 260)
        worksheet.col(7).width = int(25 * 260)
        worksheet.col(8).width = int(25 * 260)

        # Get Data
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_cus_sale_analysis_doc']
        both_order_list = report._get_report_values(
            docids=None, data=datas).get('both_order_list')
        both_product_list = report._get_report_values(
            docids=None, data=datas).get('both_product_list')

        row = 2
        if self.report_by == 'order':
            if both_order_list:
                row = row + 2
                total_sale_amount = 0.0
                total_amount_paid = 0.0
                total_balance = 0.0
                worksheet.write(row, 0, "Order Number", bold)
                worksheet.write(row, 1, "Customer", bold)
                worksheet.write(row, 2, "Order Date", bold)
                worksheet.write(row, 3, "Salesperson", bold)
                worksheet.write(row, 4, "Sales Amount", bold)
                worksheet.write(row, 5, "Amount Paid", bold)
                worksheet.write(row, 6, "Balance", bold)
                row = row + 1
                for rec in both_order_list:
                    worksheet.write(row, 0, str(rec.get(
                        'order_number')), center)
                    worksheet.write(row, 1, str(
                        rec.get('customer_name')), center)
                    worksheet.write(row, 2, str(
                        rec.get('order_date')), center)
                    worksheet.write(row, 3, rec.get('salesperson'), center)
                    worksheet.write(row, 4, str(
                        rec.get('sale_currency_symbol'))+str("{:.2f}".format(rec.get('sale_amount'))), center)
                    worksheet.write(row, 5, str(
                        rec.get('sale_currency_symbol')) + str("{:.2f}".format(rec.get('paid_amount'))), center)
                    worksheet.write(row, 6, str(
                        rec.get('sale_currency_symbol')) + str("{:.2f}".format(rec.get('balance_amount'))), center)
                    total_sale_amount = total_sale_amount + \
                        rec.get('sale_amount')
                    total_amount_paid = total_amount_paid + \
                        rec.get('paid_amount')
                    total_balance = total_balance + \
                        rec.get('balance_amount')
                    row = row + 1
                worksheet.write(row, 3, "Total", left)
                worksheet.write(row, 4, "{:.2f}".format(
                    total_sale_amount), bold_center_total)
                worksheet.write(row, 5, "{:.2f}".format(
                    total_amount_paid), bold_center_total)
                worksheet.write(row, 6, "{:.2f}".format(
                    total_balance), bold_center_total)
                row = row + 2
        elif self.report_by == 'product':
            if both_product_list:
                row = row + 2
                total_tax = 0.0
                total_subtotal = 0.0
                total_total = 0.0
                total_balance = 0.0
                worksheet.write(row, 0, "Number", bold)
                worksheet.write(row, 1, "Date", bold)
                worksheet.write(row, 2, "Product", bold)
                worksheet.write(row, 3, "Price", bold)
                worksheet.write(row, 4, "Quantity", bold)
                worksheet.write(row, 5, "Disc.(%)", bold)
                worksheet.write(row, 6, "Tax", bold)
                worksheet.write(row, 7, "Subtotal", bold)
                worksheet.write(row, 8, "Total", bold)
                row = row + 1
                for rec in both_product_list:
                    worksheet.write(row, 0, rec.get(
                        'order_number'), center)
                    worksheet.write(row, 1, str(
                        rec.get('order_date')), center)
                    worksheet.write(row, 2, rec.get(
                        'product_name'), center)
                    worksheet.write(row, 3, str(
                        rec.get('sale_currency_symbol'))+str("{:.2f}".format(rec.get('price'))), center)
                    worksheet.write(row, 4, rec.get('qty'), center)
                    worksheet.write(row, 5, rec.get('discount'), center)
                    worksheet.write(row, 6, str(
                        rec.get('sale_currency_symbol'))+str("{:.2f}".format(rec.get('tax'))), center)
                    worksheet.write(row, 7, str(
                        rec.get('sale_currency_symbol'))+str("{:.2f}".format(rec.get('subtotal'))), center)
                    worksheet.write(row, 8, str(
                        rec.get('sale_currency_symbol'))+str("{:.2f}".format(rec.get('total'))), center)
                    total_tax = total_tax + rec.get('tax')
                    total_subtotal = total_subtotal + rec.get('subtotal')
                    total_total = total_total + rec.get('total')
                    row = row + 1
                worksheet.write(row, 5, "Total", left)
                worksheet.write(row, 6, "{:.2f}".format(
                    total_tax), bold_center_total)
                worksheet.write(row, 7, "{:.2f}".format(
                    total_subtotal), bold_center_total)
                worksheet.write(row, 8, "{:.2f}".format(
                    total_total), bold_center_total)
                row = row + 2

        filename = 'Customer Sales Analysis.xls'
        fp = BytesIO()
        workbook.save(fp)
        data = encodebytes(fp.getvalue())
        ir_attachment = self.env["ir.attachment"]
        attachment_vals = {
            "name": filename,
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = ir_attachment.search([
            ("name", "=", filename),
            ("type", "=", "binary"),
            ("res_model", "=", "ir.ui.view"),], limit=1,)
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = ir_attachment.create(attachment_vals)

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}
