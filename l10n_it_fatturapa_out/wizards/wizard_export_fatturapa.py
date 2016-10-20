# -*- coding: utf-8 -*-
# Copyright (C) 2014 Davide Corio
# Copyright 2015-2016 Lorenzo Battistini - Agile Business Group
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from unidecode import unidecode

from pyxb.exceptions_ import SimpleFacetValueError, SimpleTypeValueError

from odoo import models, api, _
from odoo.exceptions import UserError

from odoo.addons.l10n_it_fatturapa.bindings.fatturapa_v_1_1 import (
    FatturaElettronica,
    FatturaElettronicaHeaderType,
    DatiTrasmissioneType,
    IdFiscaleType,
    ContattiTrasmittenteType,
    CedentePrestatoreType,
    AnagraficaType,
    IndirizzoType,
    IscrizioneREAType,
    CessionarioCommittenteType,
    DatiAnagraficiCedenteType,
    DatiAnagraficiCessionarioType,
    FatturaElettronicaBodyType,
    DatiGeneraliType,
    DettaglioLineeType,
    DatiBeniServiziType,
    DatiRiepilogoType,
    DatiGeneraliDocumentoType,
    DatiDocumentiCorrelatiType,
    ContattiType,
    DatiPagamentoType,
    DettaglioPagamentoType,
    AllegatiType
)
from odoo.addons.l10n_it_fatturapa.models.account import (
    RELATED_DOCUMENT_TYPES)


class WizardExportFatturapa(models.TransientModel):
    _name = "wizard.export.fatturapa"
    _description = "Export FatturaPA"

    def __init__(self):
        self.fatturapa = False
        self.number = False
        self.company = False
        self.partner = False
        self.invoice = False
        super(WizardExportFatturapa, self).__init__()

    def saveAttachment(self):
        number = self.number
        if not self.company.vat:
            raise UserError( _('Company TIN not set.'))
        attach_obj = self.env['fatturapa.attachment.out']
        attach_vals = {
            'name': '%s_%s.xml' % (company.vat, str(number)),
            'datas_fname': '%s_%s.xml' % (company.vat, str(number)),
            'datas': base64.encodestring(self.fatturapa.toxml("latin1")),
        }
        attach_id = attach_obj.create(attach_vals)

        return attach_id

    def setProgressivoInvio(self):
        fatturapa_sequence = self.company.fatturapa_sequence_id
        if not fatturapa_sequence:
            raise UserError( _('FatturaPA sequence not configured.'))
        self.number = number = (
            fatturapa_sequence.next_by_id(
                fatturapa_sequence.id)
            )
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            ProgressivoInvio = number

    def _setIdTrasmittente(self):
        if not self.company.country_id:
            raise UserError( _('Company Country not set.'))
        IdPaese = self.company.country_id.code

        IdCodice = self.company.partner_id.fiscalcode
        if not IdCodice:
            IdCodice = self.company.vat[2:]
        if not IdCodice:
            raise UserError(
                _('Error'), _('Company does not have fiscal code or VAT'))

        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            IdTrasmittente = IdFiscaleType(
                IdPaese=IdPaese, IdCodice=IdCodice)

    def _setFormatoTrasmissione(self):
        if not self.company.fatturapa_format_id:
            raise UserError( _('FatturaPA format not set.'))
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            FormatoTrasmissione = self.company.fatturapa_format_id.code

    def _setCodiceDestinatario(self):
        code =self.partner.ipa_code
        if not code:
            raise UserError( _('IPA Code not set onself.partner form.'))
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            CodiceDestinatario = code.upper()

    def _setContattiTrasmittente(self):

        if not self.company.phone:
            raise UserError( _('Company Telephone number not set.'))
        Telefono = self.company.phone

        if not self.company.email:
            raise UserError( _('Email address not set.'))
        Email = self.company.email
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            ContattiTrasmittente = ContattiTrasmittenteType(
                Telefono=Telefono, Email=Email)


    def setDatiTrasmissione(self):
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione = (
            DatiTrasmissioneType())
        self._setIdTrasmittente()
        self._setFormatoTrasmissione()
        self._setCodiceDestinatario()
        self._setContattiTrasmittente()

    def _setDatiAnagraficiCedente(self, CedentePrestatore):
        if not self.company.vat:
            raise UserError( _('TIN not set.'))
        CedentePrestatore.DatiAnagrafici = DatiAnagraficiCedenteType()
        fatturapa_fp = self.company.fatturapa_fiscal_position_id
        if not fatturapa_fp:
            raise UserError( _('FatturaPA fiscal position not set.'))
        CedentePrestatore.DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
            IdPaese=company.country_id.code, IdCodice=company.vat[2:])
        CedentePrestatore.DatiAnagrafici.Anagrafica = AnagraficaType(
            Denominazione=company.name)

        # not using for now
        #
        # Anagrafica = DatiAnagrafici.find('Anagrafica')
        # Nome = Anagrafica.find('Nome')
        # Cognome = Anagrafica.find('Cognome')
        # Titolo = Anagrafica.find('Titolo')
        # Anagrafica.remove(Nome)
        # Anagrafica.remove(Cognome)
        # Anagrafica.remove(Titolo)

        if self.company.partner_id.fiscalcode:
            CedentePrestatore.DatiAnagrafici.CodiceFiscale = (
                self.company.partner_id.fiscalcode)
        CedentePrestatore.DatiAnagrafici.RegimeFiscale = fatturapa_fp.code
        return True

    def _setAlboProfessionaleCedente(self, CedentePrestatore):
        pass
        # TODO Albo professionale, for now the main self.company is considered
        # to be a legal entity and not a single person
        # 1.2.1.4   <AlboProfessionale>
        # 1.2.1.5   <ProvinciaAlbo>
        # 1.2.1.6   <NumeroIscrizioneAlbo>
        # 1.2.1.7   <DataIscrizioneAlbo>

    def _setSedeCedente(self, CedentePrestatore):

        if not self.company.street:
            raise UserError( _('Street not set.'))
        if not self.company.zip:
            raise UserError( _('ZIP not set.'))
        if not self.company.city:
            raise UserError( _('City not set.'))
        if not self.company.partner_id.state_id:
            raise UserError( _('Province not set.'))
        if not self.company.country_id:
            raise UserError( _('Country not set.'))
        # FIXME: manage address number in <NumeroCivico>
        # see https://github.com/OCA/partner-contact/pull/96
        CedentePrestatore.Sede = IndirizzoType(
            Indirizzo=company.street,
            CAP=company.zip,
            Comune=company.city,
            Provincia=company.partner_id.state_id.code,
            Nazione=company.country_id.code)

        return True

    def _setStabileOrganizzazione(self, CedentePrestatore):
        pass
        # not handled

    def _setRea(self, CedentePrestatore):
        if self.company.fatturapa_rea_office and self.company.fatturapa_rea_number:
            CedentePrestatore.IscrizioneREA = IscrizioneREAType(
                Ufficio=(
                    self.company.fatturapa_rea_office and
                    self.company.fatturapa_rea_office.code or None),
                NumeroREA=company.fatturapa_rea_number or None,
                CapitaleSociale=(
                    self.company.fatturapa_rea_capital and
                    '%.2f' % self.company.fatturapa_rea_capital or None),
                SocioUnico=(company.fatturapa_rea_partner or None),
                StatoLiquidazione=company.fatturapa_rea_liquidation or None
            )

    def _setContatti(self, CedentePrestatore):
        CedentePrestatore.Contatti = ContattiType(
            Telefono=company.partner_id.phone or None,
            Fax=company.partner_id.fax or None,
            Email=company.partner_id.email or None
        )

    def _setPubAdministrationRef(self, CedentePrestatore):
        if self.company.fatturapa_pub_administration_ref:
            CedentePrestatore.RiferimentoAmministrazione = (
                self.company.fatturapa_pub_administration_ref)

    def setCedentePrestatore(self):
        self.fatturapa.FatturaElettronicaHeader.CedentePrestatore = (
            CedentePrestatoreType())
        self._setDatiAnagraficiCedente(
            self.fatturapa.FatturaElettronicaHeader.CedentePrestatore)
        self._setSedeCedente(
            self.fatturapa.FatturaElettronicaHeader.CedentePrestatore)
        self._setAlboProfessionaleCedente(
            self.fatturapa.FatturaElettronicaHeader.CedentePrestatore)
        self._setStabileOrganizzazione(
            self.fatturapa.FatturaElettronicaHeader.CedentePrestatore)
        # FIXME: add Contacts
        self._setRea(
            self.fatturapa.FatturaElettronicaHeader.CedentePrestatore)
        self._setContatti(
            self.fatturapa.FatturaElettronicaHeader.CedentePrestatore)
        self._setPubAdministrationRef(
            self.fatturapa.FatturaElettronicaHeader.CedentePrestatore)

    def _setDatiAnagraficiCessionario(self):
        self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
            DatiAnagrafici = DatiAnagraficiCessionarioType()
        if notself.partner.vat and notself.partner.fiscalcode:
            raise UserError( _('Partner VAT and Fiscalcode not set.'))
        ifself.partner.fiscalcode:
            self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
                DatiAnagrafici.CodiceFiscale =self.partner.fiscalcode
        ifself.partner.vat:
            self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
                DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
                    IdPaese=partner.vat[0:2], IdCodice=partner.vat[2:])
        self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
            DatiAnagrafici.Anagrafica = AnagraficaType(
                Denominazione=partner.name)

        # not using for now
        #
        # Anagrafica = DatiAnagrafici.find('Anagrafica')
        # Nome = Anagrafica.find('Nome')
        # Cognome = Anagrafica.find('Cognome')
        # Titolo = Anagrafica.find('Titolo')
        # Anagrafica.remove(Nome)
        # Anagrafica.remove(Cognome)
        # Anagrafica.remove(Titolo)

        ifself.partner.eori_code:
            self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
                DatiAnagrafici.Anagrafica.CodEORI =self.partner.eori_code

        return True

    def _setSedeCessionario(self):

        if not self.partner.street:
            raise UserError( _('Customer street not set.'))
        if not self.partner.zip:
            raise UserError( _('Customer ZIP not set.'))
        if not self.partner.city:
            raise UserError( _('Customer city not set.'))
        if not self.partner.state_id:
            raise UserError( _('Customer province not set.'))
        if not self.partner.country_id:
            raise UserError( _('Customer country not set.'))

        # TODO FIXME: manage address number in <NumeroCivico>
        self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.Sede = (
            IndirizzoType(
                Indirizzo=self.partner.street,
                CAP=self.partner.zip,
                Comune=self.partner.city,
                Provincia=self.partner.state_id.code,
                Nazione=self.partner.country_id.code))

    def setRappresentanteFiscale(self):

        if self.company.fatturapa_tax_representative:
            # TODO: RappresentanteFiscale should be usefull for foreign
            # companies sending self.invoices to italian PA only
            raise UserError( _("RappresentanteFiscale not handled"))
            #self.partner = self.company.fatturapa_tax_representative

        # DatiAnagrafici = RappresentanteFiscale.find('DatiAnagrafici')

        # if notself.partner.fiscalcode:
            # raise UserError(
            # _('Error!'), _('RappresentanteFiscaleself.partner '
            # 'fiscalcode not set.'))

        # DatiAnagrafici.find('CodiceFiscale').text =self.partner.fiscalcode

        # if notself.partner.vat:
            # raise UserError(
            # _('Error!'), _('RappresentanteFiscaleself.partner VAT not set.'))
        # DatiAnagrafici.find(
            # 'IdFiscaleIVA/IdPaese').text =self.partner.vat[0:2]
        # DatiAnagrafici.find(
            # 'IdFiscaleIVA/IdCodice').text =self.partner.vat[2:]
        # DatiAnagrafici.find('Anagrafica/Denominazione').text =self.partner.name
        # ifself.partner.eori_code:
            # DatiAnagrafici.find(
            # 'Anagrafica/CodEORI').text =self.partner.codiceEORI


    def setCessionarioCommittente(self):
        self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente = (
            CessionarioCommittenteType())
        self._setDatiAnagraficiCessionario()
        self._setSedeCessionario()

    def setTerzoIntermediarioOSoggettoEmittente(self):
        if self.company.fatturapa_sender_partner:
            # TODO Terzo intermediario
            raise UserError(
                _("TerzoIntermediarioOSoggettoEmittente not handled"))
        return True

    def setSoggettoEmittente(self):

        # TODO  FIXME: this record is to be checked self.invoice
        # by self.invoice
        # so a control is needed to verify that all self.invoices are
        # of type CC, TZ or internally created by the self.company
        pass

    def setDatiGeneraliDocumento(self, self.invoice, body):
        # TODO DatiSAL
        # TODO DatiDDT`
        body.DatiGenerali = DatiGeneraliType()
        if not self.invoice.number:
            raise UserError(
                _('Invoice does not have a number.'))

        TipoDocumento = 'TD01'
        if self.invoice.type == 'out_refund':
            TipoDocumento = 'TD04'
        ImportoTotaleDocumento = self.invoice.amount_total
        if self.invoice.split_payment:
            ImportoTotaleDocumento += self.invoice.amount_sp
        body.DatiGenerali.DatiGeneraliDocumento = DatiGeneraliDocumentoType(
            TipoDocumento=TipoDocumento,
            Divisa=invoice.currency_id.name,
            Data=invoice.date_invoice,
            Numero=invoice.number,
            ImportoTotaleDocumento='%.2f' % ImportoTotaleDocumento)

        # TODO: DatiRitenuta, DatiBollo, DatiCassaPrevidenziale,
        # ScontoMaggiorazione, Arrotondamento,

        if self.invoice.comment:
            # max length of Causale is 200
            caus_list = self.invoice.comment.split('\n')
            for causale in caus_list:
                # Remove non latin chars, but go back to unicode string,
                # as expected by String200LatinType
                causale = causale.encode(
                    'latin', 'ignore').decode('latin')
                body.DatiGenerali.DatiGeneraliDocumento.Causale.append(causale)

        if self.invoice.company_id.fatturapa_art73:
            body.DatiGenerali.DatiGeneraliDocumento.Art73 = 'SI'

    def setRelatedDocumentTypes(self, body):
        linecount = 1
        for line in self.invoice.invoice_line:
            for related_document in line.related_documents:
                doc_type = RELATED_DOCUMENT_TYPES[related_document.type]
                documento = DatiDocumentiCorrelatiType()
                if related_document.name:
                    documento.IdDocumento = related_document.name
                if related_document.lineRef:
                    documento.RiferimentoNumeroLinea.append(linecount)
                if related_document.date:
                    documento.Data = related_document.date
                if related_document.numitem:
                    documento.NumItem = related_document.numitem
                if related_document.code:
                    documento.CodiceCommessaConvenzione = related_document.code
                if related_document.cup:
                    documento.CodiceCUP = related_document.cup
                if related_document.cig:
                    documento.CodiceCIG = related_document.cig
                getattr(body.DatiGenerali, doc_type).append(documento)
            linecount += 1
        for related_document in self.invoice.related_documents:
            doc_type = RELATED_DOCUMENT_TYPES[related_document.type]
            documento = DatiDocumentiCorrelatiType()
            if related_document.name:
                documento.IdDocumento = related_document.name
            if related_document.date:
                documento.Data = related_document.date
            if related_document.numitem:
                documento.NumItem = related_document.numitem
            if related_document.code:
                documento.CodiceCommessaConvenzione = related_document.code
            if related_document.cup:
                documento.CodiceCUP = related_document.cup
            if related_document.cig:
                documento.CodiceCIG = related_document.cig
            getattr(body.DatiGenerali, doc_type).append(documento)

    def setDatiTrasporto(self, body):
        pass

    def setDettaglioLinee(self, body):
        body.DatiBeniServizi = DatiBeniServiziType()
        # TipoCessionePrestazione not handled

        # TODO CodiceArticolo

        line_no = 1
        for line in self.invoice.invoice_line:
            if not line.invoice_line_tax_id:
                raise UserError(
                    _('Error'),
                    _("Invoice line %s does not have tax") % line.name)
            if len(line.invoice_line_tax_id) > 1:
                raise UserError(
                    _('Error'),
                    _("Too many taxes for self.invoice line %s") % line.name)
            aliquota = line.invoice_line_tax_id[0].amount*100
            AliquotaIVA = '%.2f' % (aliquota)
            DettaglioLinea = DettaglioLineeType(
                NumeroLinea=str(line_no),
                Descrizione=line.name,
                PrezzoUnitario='%.2f' % line.price_unit,
                Quantita='%.2f' % line.quantity,
                UnitaMisura=line.uos_id and (
                    unidecode(line.uos_id.name)) or None,
                PrezzoTotale='%.2f' % line.price_subtotal,
                AliquotaIVA=AliquotaIVA)
            if aliquota == 0.0:
                if not line.invoice_line_tax_id[0].non_taxable_nature:
                    raise UserError(
                        _("No 'nature' field for tax %s") %
                        line.invoice_line_tax_id[0].name)
                DettaglioLinea.Natura = line.invoice_line_tax_id[
                    0
                ].non_taxable_nature
            if line.admin_ref:
                DettaglioLinea.RiferimentoAmministrazione = line.admin_ref
            line_no += 1

            # not handled

            # el.remove(el.find('DataInizioPeriodo'))
            # el.remove(el.find('DataFinePeriodo'))
            # el.remove(el.find('ScontoMaggiorazione'))
            # el.remove(el.find('Ritenuta'))
            # el.remove(el.find('AltriDatiGestionali'))

            body.DatiBeniServizi.DettaglioLinee.append(DettaglioLinea)

    def setDatiRiepilogo(self, body):
        tax_pool = self.env['account.tax']
        for tax_line in self.invoice.tax_line:
            tax_id = self.env['account.tax'].get_tax_by_invoice_tax(
                tax_line.name)
            tax = tax_pool.browse(tax_id)
            riepilogo = DatiRiepilogoType(
                AliquotaIVA='%.2f' % (tax.amount * 100),
                ImponibileImporto='%.2f' % tax_line.base,
                Imposta='%.2f' % tax_line.amount
            )
            if tax.amount == 0.0:
                if not tax.non_taxable_nature:
                    raise UserError(
                        _("No 'nature' field for tax %s") % tax.name)
                riepilogo.Natura = tax.non_taxable_nature
                if not tax.law_reference:
                    raise UserError(
                        _("No 'law reference' field for tax %s") % tax.name)
                riepilogo.RiferimentoNormativo = tax.law_reference
            if tax.payability:
                riepilogo.EsigibilitaIVA = tax.payability
            # TODO

            # el.remove(el.find('SpeseAccessorie'))
            # el.remove(el.find('Arrotondamento'))

            body.DatiBeniServizi.DatiRiepilogo.append(riepilogo)

    def setDatiPagamento(self, body):
        if self.invoice.payment_term:
            DatiPagamento = DatiPagamentoType()
            if not self.invoice.payment_term.fatturapa_pt_id:
                raise UserError(
                    _('Error'),
                    _('Payment term %s does not have a linked fatturaPA '
                      'payment term') % self.invoice.payment_term.name)
            if not self.invoice.payment_term.fatturapa_pm_id:
                raise UserError(
                    _('Error'),
                    _('Payment term %s does not have a linked fatturaPA '
                      'payment method') % self.invoice.payment_term.name)
            DatiPagamento.CondizioniPagamento = (
                self.invoice.payment_term.fatturapa_pt_id.code)
            move_line_pool = self.env['account.move.line']
            self.invoice_pool = self.env['account.invoice']
            payment_line_ids = self.invoice.move_line_id_payment_get()
            for move_line_id in payment_line_ids:
                move_line = move_line_pool.browse(
                    move_line_id)
                ImportoPagamento = '%.2f' % move_line.debit
                DettaglioPagamento = DettaglioPagamentoType(
                    ModalitaPagamento=(
                        self.invoice.payment_term.fatturapa_pm_id.code),
                    DataScadenzaPagamento=move_line.date_maturity,
                    ImportoPagamento=ImportoPagamento
                )
                if self.invoice.partner_bank_id:
                    DettaglioPagamento.IstitutoFinanziario = (
                        self.invoice.partner_bank_id.bank_name)
                    if self.invoice.partner_bank_id.acc_number:
                        DettaglioPagamento.IBAN = (
                            ''.join(invoice.partner_bank_id.acc_number.split())
                    )
                    if self.invoice.partner_bank_id.bank_bic:
                        DettaglioPagamento.BIC = (
                            self.invoice.partner_bank_id.bank_bic)
                DatiPagamento.DettaglioPagamento.append(DettaglioPagamento)
            body.DatiPagamento.append(DatiPagamento)

    def setAttachments(self, body):
        if self.invoice.fatturapa_doc_attachments:
            for doc_id in self.invoice.fatturapa_doc_attachments:
                AttachDoc = AllegatiType(
                    NomeAttachment=doc_id.datas_fname,
                    Attachment=doc_id.datas
                )
                body.Allegati.append(AttachDoc)

    def setFatturaElettronicaHeader(self):
        self.fatturapa.FatturaElettronicaHeader = (
            FatturaElettronicaHeaderType())
        self.setDatiTrasmissione()
        self.setCedentePrestatore()
        self.setRappresentanteFiscale()
        self.setCessionarioCommittente()
        self.setTerzoIntermediarioOSoggettoEmittente()
        self.setSoggettoEmittente()

    def setFatturaElettronicaBody(self, FatturaElettronicaBody):
        self.setDatiGeneraliDocumento(
            inv, FatturaElettronicaBody)
        self.setRelatedDocumentTypes(FatturaElettronicaBody)
        self.setDatiTrasporto(FatturaElettronicaBody)
        self.setDettaglioLinee(FatturaElettronicaBody)
        self.setDatiRiepilogo( FatturaElettronicaBody)
        self.setDatiPagamento(FatturaElettronicaBody)
        self.setAttachments(FatturaElettronicaBody)

    @api.multi
    def exportFatturaPA(self):
        model_data_obj = self.env['ir.model.data']
        self.invoice_obj = self.env['account.invoice']
        self.fatturapa = FatturaElettronica(versione='1.1')
        self.invoice_ids = context.get('active_ids', False)
        self.invoices = self.invoice_obj.browse(invoice_ids)
        self.partner = self.invoices.mapped('partner_id')
        if len(self.partner) > 1:
            raise orm.UserError(
                _('Invoices must belong to the sameself.partner'))

        self.company = self.env.user_id.company_id
        # context_partner = self.env._context.copy()
       # context_partner.update({'lang':self.partner.lang})
        try:
            self.setFatturaElettronicaHeader()
            for _invoice in self.invoice_ids:
                self.invoice = _invoice
                if self.invoice.fatturapa_attachment_out_id:
                    raise UserError(
                        _("Invoice %s has FatturaPA Export File yet") % (
                            self.invoice.number))
                invoice_body = FatturaElettronicaBodyType()
                self.setFatturaElettronicaBody(invoice_body)
                self.fatturapa.FatturaElettronicaBody.append(invoice_body)
                # TODO DatiVeicoli

            self.setProgressivoInvio()
        except (SimpleFacetValueError, SimpleTypeValueError) as e:
            raise UserError(
                _("XML SDI validation error"),
                (unicode(e)))

        attach_id = self.saveAttachment()

        for _invoice in self.invoice_ids:
            _invoice.write({'fatturapa_attachment_out_id': attach_id})

        mod_obj = self.env['ir.model.data']
        res = self.env.ref(
            'l10n_it_fatturapa_out.'
            'action_fatturapa_attachment')
        view_id = mod_obj.get_object_reference(
            'l10n_it_fatturapa_out',
            'view_fatturapa_out_attachment_form')
        return {
            'view_type': 'form',
            'name': "Export FatturaPA",
            'view_id': [view_id,
            'res_id': attach_id.id,
            'view_mode': 'form',
            'res_model': 'fatturapa.attachment.out',
            'type': 'ir.actions.act_window',
            'context': self.env.context
        }
