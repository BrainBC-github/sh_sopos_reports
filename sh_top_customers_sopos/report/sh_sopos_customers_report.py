# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, _
from odoo.exceptions import UserError
import operator
import pytz
from datetime import timedelta


class TopSoposCustomersReport(models.AbstractModel):
    _name = 'report.sh_sopos_reports.sh_sopos_customers_doc'
    _description = "top so and pos customers report abstract model"

    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        sale_order_obj = self.env['sale.order']
        pos_order_obj = self.env['pos.order']
        currency_id = False
        if data['date_from']:
            date_start = fields.Datetime.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            date_stop = fields.Datetime.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if date_stop < date_start:
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        ##################################
        # for partner from to
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
            ('state', 'in', ['sale', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('team_id'):
            team_id = data.get('team_id')
            team_id = team_id[0]
            domain.append(
                ('team_id', '=', team_id)
            )

        sale_orders = sale_order_obj.sudo().search(domain)
        partner_total_amount_dic = {}
        if sale_orders:
            for order in sale_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id: order.amount_total})

        final_partner_list = []
        final_partner_amount_list = []
        if partner_total_amount_dic:
            # sort partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_partner_list.append(tuple_item[0])
                    final_partner_amount_list.append(tuple_item[1])
                elif data['amount_total'] == 0:
                    final_partner_list.append(tuple_item[0])
                    final_partner_amount_list.append(tuple_item[1])

                # final_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare partner from to
        sale_orders = False
        if data['date_compare_from']:
            date_start = fields.Datetime.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            date_stop = fields.Datetime.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if date_stop < date_start:
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
            ('state', 'in', ['sale', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('team_id'):
            team_id = data.get('team_id')
            team_id = team_id[0]
            domain.append(
                ('team_id', '=', team_id)
            )

        sale_orders = sale_order_obj.sudo().search(domain)

        partner_total_amount_dic = {}
        if sale_orders:
            for order in sale_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id: order.amount_total})

        final_compare_partner_list = []
        final_compare_partner_amount_list = []
        if partner_total_amount_dic:
            # sort compare partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)

            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_compare_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_compare_partner_list.append(tuple_item[0])

                final_compare_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break
        date_start = False
        date_stop = False
        if data['date_from']:
            date_start = fields.Datetime.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            date_stop = fields.Datetime.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
            ('state', 'in', ['paid', 'done', 'invoiced']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('config_ids', False):
            session_ids = self.env['pos.session'].sudo().search(
                [('config_id', 'in', data.get('config_ids', False))])
            domain.append(('session_id', 'in', session_ids.ids))

        if data.get('team_id'):
            team_id = data.get('team_id')
            team_id = team_id[0]
            domain.append(
                ('crm_team_id', '=', team_id)
            )

        pos_orders = pos_order_obj.sudo().search(domain)
        if pos_orders:
            for pos_order in pos_orders.sorted(key=lambda o: o.partner_id.id):
                if pos_order.currency_id:
                    currency_id = pos_order.currency_id

                if partner_total_amount_dic.get(pos_order.partner_id, False):
                    amount = partner_total_amount_dic.get(
                        pos_order.partner_id)
                    amount += pos_order.amount_total
                    partner_total_amount_dic.update(
                        {pos_order.partner_id: amount})
                else:
                    partner_total_amount_dic.update(
                        {pos_order.partner_id: pos_order.amount_total})

        if partner_total_amount_dic:
            # sort partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_partner_list.append(tuple_item[0])
                    final_partner_amount_list.append(tuple_item[1])
                elif data['amount_total'] == 0:
                    final_partner_list.append(tuple_item[0])
                    final_partner_amount_list.append(tuple_item[1])

                # final_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare partner from to
        pos_orders = False
        if data['date_compare_from']:
            date_start = fields.Datetime.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            date_stop = fields.Datetime.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if date_stop < date_start:
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
            ('state', 'in', ['paid', 'done', 'invoiced']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('config_ids', False):
            session_ids = self.env['pos.session'].sudo().search(
                [('config_id', 'in', data.get('config_ids', False))])
            domain.append(('session_id', 'in', session_ids.ids))

        if data.get('team_id'):
            team_id = data.get('team_id')
            team_id = team_id[0]
            domain.append(
                ('crm_team_id', '=', team_id)
            )

        pos_orders = pos_order_obj.sudo().search(domain)

        if pos_orders:
            for pos_order in pos_orders.sorted(key=lambda o: o.partner_id.id):
                if pos_order.currency_id:
                    currency_id = pos_order.currency_id

                if partner_total_amount_dic.get(pos_order.partner_id, False):
                    amount = partner_total_amount_dic.get(
                        pos_order.partner_id)
                    amount += pos_order.amount_total
                    partner_total_amount_dic.update(
                        {pos_order.partner_id: amount})
                else:
                    partner_total_amount_dic.update(
                        {pos_order.partner_id: pos_order.amount_total})

        if partner_total_amount_dic:
            # sort compare partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_compare_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_compare_partner_list.append(tuple_item[0])

                final_compare_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_partner_list = []
        new_partner_list = []
        if final_partner_list and final_compare_partner_list:
            for item in final_partner_list:
                if item not in final_compare_partner_list:
                    lost_partner_list.append(item)

            for item in final_compare_partner_list:
                if item not in final_partner_list:
                    new_partner_list.append(item)

        # finally update data dictionary
        if not currency_id:
            self.env.user.company_id.sudo().currency_id
        if final_partner_list:
            data.update({'partners': final_partner_list,
                        'partners_amount': final_partner_amount_list,
                         'compare_partners': final_compare_partner_list,
                         'compare_partners_amount': final_compare_partner_amount_list,
                         'lost_partners': lost_partner_list,
                         'new_partners': new_partner_list,
                         'currency': currency_id,
                         })
            return data
        else:
            raise UserError(_('There is no Data Found between these dates...'))
