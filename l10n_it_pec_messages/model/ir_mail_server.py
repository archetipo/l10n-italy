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
from openerp.osv import fields, orm, osv
import openerp.tools as tools
from openerp.addons.base.ir.ir_mail_server \
    import extract_rfc2822_addresses, MailDeliveryException
import time
import imaplib
import threading
import logging
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class ir_mail_server(orm.Model):
    _inherit = "ir.mail_server"

    _columns = {
        'in_server_id':  fields.many2one(
            'fetchmail.server', 'Incoming PEC server',
            domain=[('pec', '=', True)]),
        'pec': fields.boolean(
            "Pec Server",
            help="Check if this server is PEC"),
        'pec_email': fields.char('Pec Email', help="The mail address used \
            to send pec mails"),
    }
    _sql_constraints = [
        ('incomingserver_name_unique', 'unique(in_server_id)',
         'Incoming Server already in use'),
        ]

    def send_email(self, cr, uid, message, mail_server_id=None,
                   smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None,
                   smtp_encryption=None, smtp_debug=False,
                   context=None):
        smtp_from = message['Return-Path'] or message['From']
        assert smtp_from, "The Return-Path or From header \
            is required for any outbound email"

        # The email's "Envelope From" (Return-Path),
        # and all recipient addresses must only contain ASCII characters.
        from_rfc2822 = extract_rfc2822_addresses(smtp_from)
        assert from_rfc2822, ("Malformed 'Return-Path' \
                                or 'From' address: %r - "
                              "It should contain one valid plain ASCII email"
                              ) % smtp_from
        # use last extracted email,
        # to support rarities like 'Support@MyComp <support@mycompany.com>'
        smtp_from = from_rfc2822[-1]
        email_to = message['To']
        email_cc = message['Cc']
        email_bcc = message['Bcc']
        smtp_to_list = filter(None,
                              tools.flatten(map(extract_rfc2822_addresses,
                                            [email_to,
                                             email_cc,
                                             email_bcc])))
        assert smtp_to_list, "At least one valid recipient address should be \
            specified for outgoing emails (To/Cc/Bcc)"

        # Do not actually send emails in testing mode!
        if getattr(threading.currentThread(), 'testing', False):
            _logger.log(logging.TEST, "skip sending email in test mode")
            return message['Message-Id']

        # Get SMTP Server Details from Mail Server
        mail_server = None
        if mail_server_id:
            mail_server = self.browse(cr, SUPERUSER_ID, mail_server_id)
        elif not smtp_server:
            mail_server_ids = self.search(cr, SUPERUSER_ID, [],
                                          order='sequence', limit=1)
            if mail_server_ids:
                mail_server = self.browse(cr, SUPERUSER_ID, mail_server_ids[0])

        if mail_server:
            smtp_server = mail_server.smtp_host
            smtp_user = mail_server.smtp_user
            smtp_password = mail_server.smtp_pass
            smtp_port = mail_server.smtp_port
            smtp_encryption = mail_server.smtp_encryption
            smtp_debug = smtp_debug or mail_server.smtp_debug
        else:
            # we were passed an explicit smtp_server or nothing at all
            smtp_server = smtp_server or tools.config.get('smtp_server')
            smtp_port = tools.config.get('smtp_port', 25) if \
                smtp_port is None else smtp_port
            smtp_user = smtp_user or tools.config.get('smtp_user')
            smtp_password = smtp_password or tools.config.get('smtp_password')
            if smtp_encryption is None and tools.config.get('smtp_ssl'):
                # STARTTLS is the new meaning of the smtp_ssl flag as of v7.0
                smtp_encryption = 'starttls'

        if not smtp_server:
            raise osv.except_osv(
                _("Missing SMTP Server"),
                _("Please define at least one SMTP server, \
                 or provide the SMTP parameters explicitly."))
        # Set IMAP
        fetchmail_server_model = self.pool.get('fetchmail.server')
        try:
            message_id = message['Message-Id']

            # Add email in Maildir if smtp_server contains maildir.
            if smtp_server.startswith('maildir:/'):
                from mailbox import Maildir
                maildir_path = smtp_server[8:]
                mdir = Maildir(maildir_path, factory=None, create=True)
                mdir.add(message.as_string(True))
                return message_id

            try:
                smtp = self.connect(smtp_server,
                                    smtp_port,
                                    smtp_user,
                                    smtp_password,
                                    smtp_encryption or False,
                                    smtp_debug)
                smtp.sendmail(smtp_from, smtp_to_list, message.as_string())
                # Save sent mail
                try:
                    if mail_server and mail_server.pec and \
                            mail_server.in_server_id.sent_folder_name:
                        imap_conn = fetchmail_server_model.connect(
                            cr,
                            SUPERUSER_ID,
                            mail_server.in_server_id.id,
                            context=context
                            )
                        imap_conn.append(mail_server.in_server_id.
                                         sent_folder_name,
                                         '\\Seen',
                                         imaplib.Time2Internaldate(
                                             time.time()),
                                         message.as_string()
                                         )
                except Exception, e:
                    for info in e:
                        _logger.info(str(info))
                    _logger.warning("Message: %s not saved"
                                    "in Sent Folder!" % str(message_id))
            finally:
                try:
                    # Close Connection of SMTP Server
                    smtp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        except Exception, e:
            msg = _("Mail delivery failed via SMTP server '%s'.\n%s: %s") \
                % (tools.ustr(smtp_server),
                   e.__class__.__name__,
                   tools.ustr(e))
            _logger.exception(msg)
            raise MailDeliveryException(_("Mail delivery failed"), msg)
        return message_id
