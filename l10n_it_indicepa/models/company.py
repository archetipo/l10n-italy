# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Davide Corio <davide.corio@lsweb.it>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, orm


class res_company(orm.Model):
    _inherit = 'res.company'
    _columns = {
        'indicepa_open_data_url': fields.char('OpenData URL', size=256),
        'indicepa_ldap_server': fields.char('LDAP Server', size=256),
        'indicepa_ldap_port': fields.integer('LDAP Port'),
        'indicepa_ldap_base_dn': fields.char('LDAP Base DN', size=246),
        'indicepa_ldap_username': fields.char('LDAP Username', size=64),
        'indicepa_ldap_password': fields.char('LDAP Password', size=64),
    }

    _defaults = {
        'indicepa_open_data_url': "http://www.indicepa.gov.it/public-services/\
opendata-read-service.php?dstype=FS&filename=serv_fatt.txt",
        'indicepa_ldap_server': 'www.indicepa.gov.it',
        'indicepa_ldap_port': 389,
        'indicepa_ldap_base_dn': 'c=it',
    }


class account_config_settings(orm.TransientModel):
    _inherit = 'account.config.settings'
    _columns = {
        'indicepa_open_data_url': fields.related(
            'company_id', 'indicepa_open_data_url',
            type='char',
            string="OpenData URL",
            ),
        'indicepa_ldap_server': fields.related(
            'company_id', 'indicepa_ldap_server',
            type='char',
            string="LDAP Server",
            ),
        'indicepa_ldap_port': fields.related(
            'company_id', 'indicepa_ldap_port',
            type='char',
            string="LDAP Port",
            ),
        'indicepa_ldap_base_dn': fields.related(
            'company_id', 'indicepa_ldap_base_dn',
            type='char',
            string="LDAP Base DN",
            ),
        'indicepa_ldap_username': fields.related(
            'company_id', 'indicepa_ldap_username',
            type='char',
            string="LDAP Username",
            ),
        'indicepa_ldap_password': fields.related(
            'company_id', 'indicepa_ldap_password',
            type='char',
            string="LDAP Password",
            ),
    }

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        res = super(account_config_settings, self).onchange_company_id(
            cr, uid, ids, company_id, context=context)
        if company_id:
            company = self.pool.get('res.company').browse(
                cr, uid, company_id, context=context)
            res['value'].update({
                'indicepa_open_data_url': (
                    company.indicepa_open_data_url or '',
                    ),
                'indicepa_ldap_server': (
                    company.indicepa_ldap_server or '',
                    ),
                'indicepa_ldap_port': (
                    company.indicepa_ldap_port or '',
                    ),
                'indicepa_ldap_base_dn': (
                    company.indicepa_ldap_base_dn or '',
                    ),
                'indicepa_ldap_username': (
                    company.indicepa_ldap_username or '',
                    ),
                'indicepa_ldap_password': (
                    company.indicepa_ldap_password or '',
                    ),
                })
        else:
            res['value'].update({
                'indicepa_open_data_url': False,
                'indicepa_ldap_server': False,
                'indicepa_ldap_port': False,
                'indicepa_ldap_base_dn': False,
                'indicepa_ldap_username': False,
                'indicepa_ldap_password': False,
                })
        return res
