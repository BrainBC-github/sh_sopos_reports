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


class SaleByCategoryWizard(models.TransientModel):
    _name = "sh.sale.category.wizard"
    _description = "Sale By Category Wizard"

    sh_start_date = fields.Datetime(
        "Start Date", required=True, default=fields.Datetime.now)
    sh_end_date = fields.Datetime(
        "End Date", required=True, default=fields.Datetime.now)
    sh_category_ids = fields.Many2many("product.category", string="Categories")
    sh_session_id = fields.Many2one("pos.session", "Session")
    company_ids = fields.Many2many(
        "res.company", default=lambda self: self.env.companies, string="Companies")

    @api.constrains("sh_start_date", "sh_end_date")
    def _check_dates(self):
        if self.filtered(lambda c: c.sh_end_date and c.sh_start_date > c.sh_end_date):
            raise ValidationError(_("start date must be less than end date."))

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref(
            "sh_sopos_reports.sh_sale_by_category_action"
        ).report_action([], data=datas)

    def display_report(self):
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_sale_by_category_doc']
        data_values = report._get_report_values(
            docids=None, data=datas).get('both_category_order_list')
        self.env['sh.sale.by.category'].search([]).unlink()
        if data_values:
            for order in data_values:
                subtotal = order['qty']*order['sale_price']
                total = subtotal+order['tax']
                self.env['sh.sale.by.category'].create({
                    'name': order['order_number'],
                    'date_order': order['order_date'],
                    'sh_product_id': order['product_id'],
                    'quantity': order['qty'],
                    'price': order['sale_price'],
                    'sh_product_uom_id': order['uom_id'],
                    'tax': order['tax'],
                    'subtotal': subtotal,
                    'total': total,
                })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales By Product category',
            'view_mode': 'tree',
            'res_model': 'sh.sale.by.category',
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
            'Sales By Product Category', bold_center)
        worksheet.write_merge(
            0, 1, 0, 8, 'Sales By Product Category', heading_format)
        center = easyxf('align: horiz center;')
        bold_center_total = easyxf('align: horiz center;font:bold True')
        user_tz = self.env.user.tz or utc
        local = timezone(user_tz)
        start_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.sh_start_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.sh_end_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        worksheet.write_merge(2, 2, 0, 8, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(25 * 260)
        worksheet.col(1).width = int(25 * 260)
        worksheet.col(2).width = int(38 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(18 * 260)
        worksheet.col(5).width = int(25 * 260)
        worksheet.col(6).width = int(25 * 260)
        worksheet.col(7).width = int(25 * 260)
        worksheet.col(8).width = int(25 * 260)

        # Get Data
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_sale_by_category_doc']
        both_category_order_list = report._get_report_values(
            docids=None, data=datas).get('both_category_order_list')

        if both_category_order_list:
            row = 2
            total_qty = 0.0
            total_price = 0.0
            total_tax = 0.0
            total_subtotal = 0.0
            total = 0.0
            row = row + 2
            worksheet.write(row, 0, "Order Number", bold)
            worksheet.write(row, 1, "Order Date", bold)
            worksheet.write(row, 2, "Product", bold)
            worksheet.write(row, 3, "Quantity", bold)
            worksheet.write(row, 4, "UOM", bold)
            worksheet.write(row, 5, "Price", bold)
            worksheet.write(row, 6, "Tax", bold)
            worksheet.write(row, 7, "Subtotal", bold)
            worksheet.write(row, 8, "Total", bold)
            row = row + 1
            for rec in both_category_order_list:
                total_qty += rec.get('qty')
                total_price += rec.get('sale_price')
                total_tax += rec.get('tax')
                total_subtotal += rec.get('qty', 0.0) * \
                    rec.get('sale_price', 0.0)
                total += (rec.get('sale_price') *
                          rec.get('qty', '')) + rec.get('tax')
                worksheet.write(row, 0, rec.get('order_number'), center)
                worksheet.write(row, 1, str(rec.get('order_date')), center)
                worksheet.write(row, 2, rec.get('product'), center)
                worksheet.write(row, 3, str(
                    "{:.2f}".format(rec.get('qty'))), center)
                worksheet.write(row, 4, rec.get('uom'), center)
                worksheet.write(row, 5, str(rec.get(
                    'sale_currency_symbol')) + str("{:.2f}".format(rec.get('sale_price'))), center)
                worksheet.write(row, 6, str(rec.get('sale_currency_symbol')) +
                                str("{:.2f}".format(rec.get('tax'))), center)
                worksheet.write(row, 7, str(rec.get('sale_currency_symbol')) + str(
                    "{:.2f}".format(rec.get('sale_price') * rec.get('qty', ''))), center)
                worksheet.write(row, 8, str(rec.get('sale_currency_symbol')) + str("{:.2f}".format(
                    (rec.get('sale_price') * rec.get('qty', '')) + rec.get('tax'))), center)
                row = row + 1
            worksheet.write(row, 2, "Total", bold_center_total)
            worksheet.write(row, 3, "{:.2f}".format(
                total_qty), bold_center_total)
            worksheet.write(row, 5, "{:.2f}".format(
                total_price), bold_center_total)
            worksheet.write(row, 6, "{:.2f}".format(
                total_tax), bold_center_total)
            worksheet.write(row, 7, "{:.2f}".format(
                total_subtotal), bold_center_total)
            worksheet.write(row, 8, "{:.2f}".format(
                total), bold_center_total)
            row = row + 2

        filename = 'Sales By Product Category.xls'
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
