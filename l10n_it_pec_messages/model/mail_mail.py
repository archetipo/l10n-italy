# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Associazione Odoo Italia
#    (<http://www.odoo-italia.org>).
#    Copyright 2014 Agile Business Group http://www.agilebg.com
#    @authors
#       Alessio Gerace <alessio.gerace@gmail.com>
#       Lorenzo Battistini <lorenzo.battistini@agilebg.com>
#       Roberto Onnis <roberto.onnis@innoviu.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from openerp.osv import orm


class MailMail(orm.Model):
    _inherit = "mail.mail"

    def create(self, cr, uid, values, context=None):
        res = super(MailMail, self).create(cr, uid, values, context=context)
        mail = self.browse(cr, uid, res, context=context)
        if (
            mail.parent_id and mail.parent_id.server_id
            and mail.parent_id.server_id.pec
        ):
            server_pool = self.pool['ir.mail_server']
            server_ids = server_pool.search(
                cr, uid, [('in_server_id', '=', mail.parent_id.server_id.id)],
                context=context)
            if server_ids:
                server = server_pool.browse(
                    cr, uid, server_ids[0], context=context)
                mail.write({
                    'email_from': server.smtp_user,
                    'mail_server_id': server.id,
                    }, context=context)
        return res