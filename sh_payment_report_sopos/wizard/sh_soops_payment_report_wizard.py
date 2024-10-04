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


class ShPaymentReportWizard(models.TransientModel):
    _name = "sh.soops.payment.report.wizard"
    _description = 'invoice payment report wizard Model'

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return False

    date_start = fields.Datetime(
        string="Start Date", required=True, default=fields.Datetime.now)
    date_end = fields.Datetime(
        string="End Date", required=True, default=fields.Datetime.now)

    state = fields.Selection([
        ('all', 'All'),
        ('open', 'Open'),
        ('paid', 'Paid'),
    ], string='Status', default='all', required=True)

    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='rel_sh_payment_report_wizard_res_user',
        string='Salesperson', domain=[('share', '=', False)])

    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)
    config_ids = fields.Many2many(
        'pos.config', string='POS Configuration', required=True)
    filter_invoice_data = fields.Selection([('all', 'Both'), ('with_invoice', 'With Invoice'), (
        'wo_invoice', 'Without Invoice')], string='POS Payments Include', default='all')

    @api.model
    def default_get(self, fields):
        rec = super(ShPaymentReportWizard, self).default_get(fields)

        search_users = self.env["res.users"].search([
            ('id', '=', self.env.user.id),
        ], limit=1)
        if self.env.user.has_group('sales_team.group_sale_salesman_all_leads') or self.env.user.has_group('point_of_sale.group_pos_manager'):
            rec.update({
                "user_ids": [(6, 0, search_users.ids)],
            })
        else:
            rec.update({
                "user_ids": [(6, 0, [self.env.user.id])],
            })
        return rec

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_end and c.date_start > c.date_end):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        datas = self.read()[0]

        return self.env.ref('sh_sopos_reports.sh_sopos_payment_report_action').report_action([], data=datas)

    def display_report(self):
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_sopos_report_doc']
        data_values = report._get_report_values(
            docids=None, data=datas).get('user_data_dic')
        self.env['sh.payment.report'].search([]).unlink()
        vals = list(data_values.values())
        for val in vals:
            dict_val = list(val.values())
            if len(val) > 0:
                for v in dict_val[0]:
                    bank = v.get('Bank', 0)
                    cash = v.get('Cash', 0)
                    customer_account = v.get('Customer Account', 0)
                    self.env['sh.payment.report'].create({
                        'name': v['Invoice'],
                        'invoice_date': v['Invoice Date'],
                        'salesperson_id': v['salesperson_id'],
                        'sh_customer_id': v['customer_id'],
                        'bank': bank,
                        'cash': cash,
                        'customer_account': customer_account,
                        'total': v['Total'],
                    })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Payment Report',
            'view_mode': 'tree',
            'res_model': 'sh.payment.report',
            'context': "{'create': False,'search_default_group_sales_person': 1}"
        }

    def print_xls_report(self):
        workbook = Workbook(encoding='utf-8', style_compression=2)
        heading_format = easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        total_bold = easyxf('font:bold True')
        bold_center = easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet('Invoice Payment Report', bold_center)

        user_tz = self.env.user.tz or utc
        local = timezone(user_tz)
        start_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.date_start), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.date_end), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        worksheet.write_merge(
            0, 1, 0, 7, 'Invoice Payment Report', heading_format)
        worksheet.write_merge(0, 1, 0, 7, 'POS Payment Report' + (' (With Invoice)' if self.filter_invoice_data ==
                              'with_invoice' else '') + (' (Without Invoice)' if self.filter_invoice_data == 'wo_invoice' else ''), heading_format)
        worksheet.write_merge(2, 2, 0, 7, start_date + " to " + end_date, bold)

        # Get Data
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_sopos_report_doc']
        user_data_dic = report._get_report_values(
            docids=None, data=datas).get('user_data_dic')
        grand_journal_dic = report._get_report_values(
            docids=None, data=datas).get('grand_journal_dic')
        columns = report._get_report_values(
            docids=None, data=datas).get('columns')

        row = 3
        col = 0

        for user in user_data_dic.keys():
            pay_list = []
            pay_list.append(user_data_dic.get(user).get('pay', []))
            row = row + 2
            worksheet.write_merge(
                row, row, 0, 7, "Sales Person: " + user, bold_center)
            row = row + 2
            col = 0
            for column in columns:
                worksheet.col(col).width = int(15 * 260)
                worksheet.write(row, col, column, bold)
                col = col + 1
            for p in pay_list:
                row = row + 1
                col = 0
                for dic in p:
                    row = row + 1
                    col = 0
                    for column in columns:
                        style = easyxf(dic.get('style', ''))
                        worksheet.write(row, col, dic.get(column, 0), style)
                        col = col + 1
            row = row + 1
            col = 3
            worksheet.col(col).width = int(15 * 260)
            worksheet.write(row, col, "Total", total_bold)
            col = col + 1
            if user_data_dic.get(user, False):
                grand_total = user_data_dic.get(user).get('grand_total', {})
                if grand_total:
                    for column in columns:
                        if column not in ['Invoice', 'Invoice Date', 'Salesperson', 'Customer']:
                            worksheet.write(row, col, grand_total.get(
                                column, 0), total_bold)
                            col = col + 1
        row = row + 2
        worksheet.write_merge(row, row, 0, 1, "Payment Method", bold)
        row = row + 1
        worksheet.write(row, 0, "Name", bold)
        worksheet.write(row, 1, "Total", bold)
        for column in columns:
            col = 0
            if column not in ["Invoice", "Invoice Date", "Salesperson", "Customer"]:
                row = row + 1
                worksheet.col(col).width = int(15 * 260)
                worksheet.write(row, col, column)
                col = col + 1
                worksheet.write(row, col, grand_journal_dic.get(column, 0))
        if grand_journal_dic.get('Refund', False):
            row = row + 1
            col = 0
            worksheet.col(col).width = int(15 * 260)
            worksheet.write(row, col, "Refund")
            worksheet.write(row, col + 1, grand_journal_dic.get('Refund', 0.0))

        filename = 'Invoice Payment Report.xls'
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
