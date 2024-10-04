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


class ShSalePosDetailsReportWizard(models.TransientModel):
    _name = "sh.sale.pos.details.report.wizard"
    _description = 'sales pos details report wizard model'

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return False

    start_date = fields.Datetime(
        string="Start Date", required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(
        string="End Date", required=True, default=fields.Datetime.now)
    state = fields.Selection([
        ('all', 'All'),
        ('done', 'Done'),
    ], string='Status', default='all', required=True)

    team_ids = fields.Many2many(
        comodel_name="crm.team",
        relation="rel_sh_sopos_reports_wizard_crm_team",
        string="Sales Channel", required=True)

    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)
    config_ids = fields.Many2many(
        'pos.config', string='POS Configuration', required=True)

    @api.model
    def default_get(self, fields):
        rec = super(ShSalePosDetailsReportWizard,
                    self).default_get(fields)

        search_teams = self.env["crm.team"].search([])
        rec.update({
            "team_ids": [(6, 0, search_teams.ids)],
        })
        return rec

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.end_date and c.start_date > c.end_date):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'team_ids': self.team_ids.ids,
                'company_ids': self.company_ids.ids, 'config_ids': self.config_ids.ids, 'state': self.state}

        return self.env.ref('sh_sopos_reports.sh_sopos_detail_report_action').report_action([], data=data)

    def display_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date,
                'team_ids': self.team_ids.ids, 'company_ids': self.company_ids.ids, 'state': self.state}
        report = self.env['report.sh_sopos_reports.sh_sopos_detail_report']
        data_values = report._get_report_values(
            docids=None, data=data).get('products')
        self.env['sh.sale.details'].search([]).unlink()
        if data_values:
            for record in data_values:
                quantity = str(record['quantity']) + " " + record['uom']
                price_unit = str(record['price_unit']) + " Disc: " + str(record['discount']) + \
                    "%" if record['discount'] != 0 else str(
                        record['price_unit']) + " "
                self.env['sh.sale.details'].create({
                    'name': record['product_id'],
                    'quantity': quantity,
                    'price_unit': price_unit,
                })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale and POS Details',
            'view_mode': 'tree',
            'res_model': 'sh.sale.details',
            'context': "{'create': False,'search_default_group_product': 1}"
        }

    def print_sale_pos_detail_xls_report(self):
        workbook = Workbook()
        heading_format = easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = easyxf(
            'font:height 225,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        b1 = easyxf('font:bold True;align: horiz left')
        bold_right = easyxf('align: horiz right')
        center = easyxf('font:bold True;align: horiz center')
        row = 1

        worksheet = workbook.add_sheet(u'Sale Details', cell_overwrite_ok=True)
        worksheet.write_merge(0, 1, 0, 3, 'Sale Details', heading_format)

        user_tz = self.env.user.tz or utc
        local = timezone(user_tz)
        start_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.start_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(utc.localize(datetime.strptime(str(
            self.end_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)

        worksheet.write_merge(2, 2, 0, 3, start_date +
                              " to " + end_date, center)

        # Get Data
        data = {'date_start': self.start_date, 'date_stop': self.end_date,
                'team_ids': self.team_ids.ids, 'company_ids': self.company_ids.ids, 'state': self.state}
        report = self.env['report.sh_sopos_reports.sh_sopos_detail_report']
        data_values_products = report._get_report_values(
            docids=None, data=data).get('products')
        data_values_payments = report._get_report_values(
            docids=None, data=data).get('payments')
        data_values_taxes = report._get_report_values(
            docids=None, data=data).get('taxes')
        data_values_total_paid = report._get_report_values(
            docids=None, data=data).get('total_paid')

        worksheet.write_merge(4, 4, 0, 3, "Products", bold_center)
        worksheet.col(0).width = int(25 * 260)
        worksheet.col(1).width = int(25 * 260)
        worksheet.col(2).width = int(12 * 260)
        worksheet.col(3).width = int(14 * 260)

        worksheet.write(5, 0, "Product", bold)
        worksheet.write(5, 1, "Quantity", bold)
        worksheet.write(5, 2, "", bold)
        worksheet.write(5, 3, "Price Unit", bold)
        row = 6
        for rec in data_values_products:
            worksheet.write(row, 0, rec['product_name'])
            worksheet.write(row, 1, str(rec['quantity']), bold_right)
            if rec['uom'] != 'Unit(s)':
                worksheet.write(row, 2, rec['uom'])
            worksheet.write(row, 3, str(rec['price_unit']), bold_right)
            row += 1
        row += 1

        if data_values_payments:
            worksheet.write_merge(row, row, 0, 3, "Payments", bold_center)
            row += 1
            worksheet.write_merge(row, row, 0, 1, "Name", bold)
            worksheet.write_merge(row, row, 2, 3, "Total", bold)
            row += 1
            for rec1 in data_values_payments:
                worksheet.write_merge(row, row, 0, 1, rec1)
                float_number = "%.2f" % data_values_payments[rec1]
                worksheet.write_merge(
                    row, row, 2, 3, str(float_number), bold_right)
                row += 1
        row += 1

        if data_values_taxes:
            worksheet.write_merge(row, row, 0, 3, "Taxes", bold_center)
            row += 1
            worksheet.write_merge(row, row, 0, 1, "Name", bold)
            worksheet.write_merge(row, row, 2, 3, "Total", bold)
            row += 1
            for rec2 in data_values_taxes:
                worksheet.write_merge(row, row, 0, 1, rec2['name'])
                worksheet.write_merge(
                    row, row, 2, 3, rec2['total'], bold_right)
                row += 1
        row += 2

        worksheet.write_merge(row, row, 0, 3, "Total: " +
                              " " + str(data_values_total_paid), b1)

        filename = 'Sale and POS Detail Xls Report.xls'
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
