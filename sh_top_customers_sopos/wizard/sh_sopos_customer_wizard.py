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


class ShSoposTopCustomerWizard(models.TransientModel):
    _name = "sh.sopos.customer.wizard"
    _description = 'Top SOPOS Customers'

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return False

    type = fields.Selection([
        ('basic', 'Basic'),
        ('compare', 'Compare'),
    ], string="Report Type", default="basic")

    date_from = fields.Datetime(
        string='From Date', required=True, default=fields.Datetime.now)
    date_to = fields.Datetime(string='To Date', required=True,
                              default=fields.Datetime.now)

    date_compare_from = fields.Datetime(
        string='Compare From Date', default=fields.Datetime.now)
    date_compare_to = fields.Datetime(
        string='Compare To Date', default=fields.Datetime.now)

    no_of_top_item = fields.Integer(
        string='No of Items', required=True, default=10)

    amount_total = fields.Monetary(string="Total Sales Amount")

    team_id = fields.Many2one("crm.team", string="Sales Channel")

    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_ids = fields.Many2many(
        'res.company', string="Company", default=default_company_ids)
    config_ids = fields.Many2many('pos.config', string='POS Configuration')

    @api.constrains('date_from', 'date_to')
    def _check_from_to_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_('from date must be less than to date.'))

    @api.constrains('date_compare_from', 'date_compare_to')
    def _check_compare_from_to_dates(self):
        if self.filtered(lambda c: c.date_compare_to and c.date_compare_from and c.date_compare_from > c.date_compare_to):
            raise ValidationError(
                _('compare from date must be less than compare to date.'))

    def print_top_customer_report(self):
        self.ensure_one()
        data = {}

        # we read self because we use from date and start date in our core bi logic.(in abstract model)
        data = self.read()[0]
        return self.env.ref('sh_sopos_reports.sh_sopos_customers_report_action').report_action([], data=data)

    def display_report(self):
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_sopos_customers_doc']
        data_values = report._get_report_values(
            docids=None, data=datas).get('partners')
        data_values_amount = report._get_report_values(
            docids=None, data=datas).get('partners_amount')
        if self.type == "basic":
            self.env['sh.top.customers'].search([]).unlink()
            length = len(data_values)
            for i in range(length):
                self.env['sh.top.customers'].create({
                    'name': data_values[i].id,
                    'sales_amount': data_values_amount[i]
                })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Top Customers',
                'view_mode': 'tree',
                'res_model': 'sh.top.customers',
                'context': "{'create': False,'search_default_group_customer': 1}"
            }

    def print_top_customer_xls_report(self,):
        workbook = Workbook()
        heading_format = easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        left = easyxf('align: horiz left')
        row = 1

        user_tz = self.env.user.tz or utc
        local = timezone(user_tz)
        basic_start_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.date_from), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        basic_end_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.date_to), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        compare_start_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.date_compare_from), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        compare_end_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.date_compare_to), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)

        # Get Data
        datas = self.read()[0]
        report = self.env['report.sh_sopos_reports.sh_sopos_customers_doc']
        data_values = report._get_report_values(
            docids=None, data=datas)
        final_partner_list = data_values.get('partners')
        final_partner_amount_list = data_values.get('partners_amount')
        final_compare_partner_list = data_values.get('compare_partners')
        final_compare_partner_amount_list = data_values.get(
            'compare_partners_amount')
        new_partner_list = data_values.get('new_partners')
        lost_partner_list = data_values.get('lost_partners')

        if self.type == 'basic':
            if final_partner_list:
                row = 1
                worksheet = workbook.add_sheet(
                    u'Top SO and POS Customers', cell_overwrite_ok=True)
                worksheet.write_merge(
                    0, 1, 0, 2, 'Top SO and POS Customers', heading_format)
                worksheet.write(3, 0, 'Date From: ', bold)
                worksheet.write(3, 1, basic_start_date)

                worksheet.write(4, 0, 'Date To: ', bold)
                worksheet.write(4, 1, basic_end_date)
                worksheet.col(0).width = int(25*260)
                worksheet.col(1).width = int(25*260)
                worksheet.col(2).width = int(18*260)
                row = 6
                worksheet.write(row, 0, "#", bold)
                worksheet.write(row, 1, "Customer", bold)
                worksheet.write(row, 2, "Sales Amount", bold)
                no = 0
                row = 7
                for index, partner in enumerate(final_partner_list):
                    worksheet.write(row, 0, index+1, left)
                    worksheet.write(
                        row, 1, partner.name or 'Walking Customer', left)
                    worksheet.write(
                        row, 2, final_partner_amount_list[index], left)
                    row = row+1

        elif self.type == 'compare':
            if final_partner_list:
                row = 1
                worksheet = workbook.add_sheet(
                    u'Top SO and POS Customers', cell_overwrite_ok=True)
                worksheet.write_merge(
                    0, 1, 0, 6, 'Top SO and POS Customers', heading_format)
                worksheet.write(3, 0, 'Date From: ', bold)
                worksheet.write(3, 1, basic_start_date)
                worksheet.write(4, 0, 'Date To: ', bold)
                worksheet.write(4, 1, basic_end_date)
                worksheet.write(3, 5, 'Compare From Date: ', bold)
                worksheet.write(3, 6, compare_start_date)

                worksheet.write(4, 5, 'Compare To Date: ', bold)
                worksheet.write(4, 6, compare_end_date)
                row = 7
                worksheet.col(0).width = int(25*260)
                worksheet.col(1).width = int(25*260)
                worksheet.col(2).width = int(18*260)
                worksheet.col(3).width = int(25*260)
                worksheet.col(4).width = int(25*260)
                worksheet.col(5).width = int(18*260)
                worksheet.col(6).width = int(18*260)
                worksheet.write(row, 0, "#", bold)
                worksheet.write(row, 1, "Customer", bold)
                worksheet.write(row, 2, "Sales Amount", bold)
                worksheet.write(row, 4, "#", bold)
                worksheet.write(row, 5, "Compare Customer", bold)
                worksheet.write(row, 6, "Sales Amount", bold)
                row = 8
                for index, partner in enumerate(final_partner_list):
                    worksheet.write(row, 0, index+1, left)
                    worksheet.write(
                        row, 1, partner.name or 'Walking Customer', left)
                    worksheet.write(
                        row, 2, final_partner_amount_list[index], left)
                    row = row+1
                final_row_partner = row
                row = 8
                for index, compare_partner in enumerate(final_compare_partner_list):
                    worksheet.write(row, 4, index+1, left)
                    worksheet.write(
                        row, 5, compare_partner.name or 'Walking Customer', left)
                    worksheet.write(
                        row, 6, final_compare_partner_amount_list[index], left)
                    row = row+1
                final_row_partner_compare = row
                # Store new_lost partner row and Lost partner row
                new_lost_partner_row = lost_partner_row = max(
                    final_row_partner, final_row_partner_compare) + 1
                worksheet.write_merge(
                    new_lost_partner_row, new_lost_partner_row, 0, 2, 'New Customers', bold_center)
                worksheet.write_merge(
                    new_lost_partner_row, new_lost_partner_row, 4, 6, 'Lost Customers', bold_center)
                # For new row of new partner and lost partner
                new_lost_partner_row = new_lost_partner_row+1
                lost_partner_row += 1
                if new_partner_list:
                    for new in new_partner_list:
                        worksheet.write_merge(
                            new_lost_partner_row, new_lost_partner_row, 0, 2, new.name or 'Walking Customer', left)
                        new_lost_partner_row = new_lost_partner_row+1
                if lost_partner_list:
                    for lost in lost_partner_list:
                        worksheet.write_merge(
                            lost_partner_row, lost_partner_row, 4, 6, lost.name or 'Walking Customer', left)
                        lost_partner_row += 1

        filename = 'Top SO and POS Customer Report.xls'
        fp = BytesIO()
        workbook.save(fp)
        data = encodebytes(fp.getvalue())
        ir_attachment = self.env['ir.attachment']
        attachment_vals = {
            'name': filename,
            'res_model': 'ir.ui.view',
            'type': 'binary',
            'datas': data,
            'public': True,
        }
        fp.close()

        attachment = ir_attachment.search([('name', '=', filename),
                                          ('type', '=', 'binary'),
                                          ('res_model', '=', 'ir.ui.view')], limit=1)
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = ir_attachment.create(attachment_vals)

        url = '/web/content/' + str(attachment.id) + '?download=true'
        return {'type': 'ir.actions.act_url', 'url': url,
                'target': 'new'}
