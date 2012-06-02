'''
Module for the C2B content message
'''

import os
from io import BytesIO
from decimal import Decimal

try:
    from bankws import timehelper
    from bankws import c2bhelper
except ImportError:
    import timehelper
    import c2bhelper

from lxml import etree as ET

NAMESPACE = 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.02'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
SCHEMA_LOCATION = NAMESPACE + ' pain.001.001.02.xsd'

DOC = ET.Element('Document',
                 attrib={'{' + XSI + '}schemaLocation': SCHEMA_LOCATION},
                 nsmap={None: NAMESPACE,
                        'xsi': XSI})
PAIN = ET.SubElement(DOC, 'pain.001.001.02')


class C2B():
    """
    C2B class is used to create the C2B-message sent to the bank

    Only SEPA payment and salary implemented.

    @type _payer: L{Entity}
    @ivar _payer: Payer's information
    @type _payments: L{SEPA}
    @ivar _payments: List of payments in this material
    @type _number_of_payments: int
    @ivar _number_of_payments: Number of payments in a message

    """

    def __init__(self, payer):
        self._payer = payer
        self._payments = []
        self._number_of_payments = 0

    def group_header(self, msg_id, grpg):
        """
        @type msg_id: string
        @param msg_id: Message ID, unique for atleast 3 months
        @type grpg: string
        @param grpg: MIXD if message has one or more PmtInf-elements.
            Other possible values are: GRPD and SNGL
        """

        self._msg_id = msg_id
        self._grpg = grpg

    def _group_header_to_xml(self, msg_id, nb_of_txs, grpg, ctrl_sum=None):
        """
        @type msg_id: string
        @param msg_id: Message ID, unique for atleast 3 months
        @type nb_of_txs: int
        @param nb_of_txs: Number of transactions in message
        @type ctrl_sum: float
        @param ctrl_sum: Arithmetic sum of fields InstdAmt
        @type grpg: string
        @param grpg: MIXD if message has one or more PmtInf-elements.
            Other possible values are: GRPD and SNGL
        """

        GRPHDR = ET.SubElement(PAIN, 'GrpHdr')
        ET.SubElement(GRPHDR, 'MsgId').text = msg_id
        ET.SubElement(GRPHDR, 'CreDtTm').text = timehelper.get_timestamp(False)
        ET.SubElement(GRPHDR, 'NbOfTxs').text = str(nb_of_txs)
        if ctrl_sum is not None:
            GRPHDR_CTRLSUM = ET.SubElement(GRPHDR, 'CtrlSum')
            GRPHDR_CTRLSUM.text = str(ctrl_sum)
        ET.SubElement(GRPHDR, 'Grpg').text = grpg
        GRPHDR_INITGPTY = ET.SubElement(GRPHDR, 'InitgPty')
        if self._payer._name is not None:
            ET.SubElement(GRPHDR_INITGPTY, 'Nm').text = self._payer._name
        if len(self._payer._address_lines) > 0:
            GRPHDR_PSTLADR = ET.SubElement(GRPHDR_INITGPTY, 'PstlAdr')
            for x in self._payer._address_lines:
                ET.SubElement(GRPHDR_PSTLADR, 'AdrLine').text = x
            ET.SubElement(GRPHDR_PSTLADR, 'Ctry').text = self._payer._country

    def add_SEPA_payment(self, sepa):
        """
        @type sepa: L{SEPA}
        @param sepa: SEPA payment to be added to the message

        @raise ValueError: If the parameter is not an instance of class SEPA
        """
        if isinstance(sepa, c2bhelper.SEPA):
            self._payments.append(sepa)
            self._number_of_payments += 1
        else:
            raise ValueError("Input object was not of type SEPA")

    def _add_SEPA_payment_to_xml(self, sepa):

        PMTINF = ET.SubElement(PAIN, 'PmtInf')
        if sepa._payment_information_id is not None:
            ET.SubElement(PMTINF, 'PmtInfId').text = sepa._payment_information_id
        ET.SubElement(PMTINF, 'PmtMtd').text = sepa._pmt_mtd
        PMTTPINF = ET.SubElement(PMTINF, 'PmtTpInf')
        # InstrPrty-value is retrieved from the transaction so it is not required here
        SVCLVL = ET.SubElement(PMTTPINF, 'SvcLvl')
        if sepa._cd is not None:
            ET.SubElement(SVCLVL, 'Cd').text = sepa._cd
        ET.SubElement(PMTINF, 'ReqdExctnDt').text = sepa._reqd_exctn_dt

        DBTR = ET.SubElement(PMTINF, 'Dbtr')
        if self._payer._name is not None:
            ET.SubElement(DBTR, 'Nm').text = self._payer._name
        if len(self._payer._address_lines) > 0:
            DBTR_PSTLADR = ET.SubElement(DBTR, 'PstlAdr')
            for x in self._payer._address_lines:
                ET.SubElement(DBTR_PSTLADR, 'AdrLine').text = x
            ET.SubElement(DBTR_PSTLADR, 'Ctry').text = self._payer._country
        DBTR_ID = ET.SubElement(DBTR, 'Id')
        DBTR_ORGID = ET.SubElement(DBTR_ID, 'OrgId')
        ET.SubElement(DBTR_ORGID, 'BkPtyId').text = sepa._material_id

        DBTRACCT = ET.SubElement(PMTINF, 'DbtrAcct')
        DBTRACCT_ID = ET.SubElement(DBTRACCT, 'Id')
        ET.SubElement(DBTRACCT_ID, 'IBAN').text = sepa._iban
        ET.SubElement(DBTRACCT, 'Ccy').text = sepa._ccy

        DBTRAGT = ET.SubElement(PMTINF, 'DbtrAgt')
        DBTRAGT_FININSTNID = ET.SubElement(DBTRAGT, 'FinInstnId')
        ET.SubElement(DBTRAGT_FININSTNID, 'BIC').text = sepa._bic

        if sepa._ultmt_dbtr is not None:
            ULTMT_DBTR = ET.SubElement(PMTINF, 'UltmtDbtr')
            ET.SubElement(ULTMT_DBTR, 'Nm').text = sepa._ultmt_dbtr

        CHRGBR = ET.SubElement(PMTINF, 'ChrgBr')
        CHRGBR.text = sepa._chrg_br

        """
        After this line starts the actual per transaction information
        """

        for tx in sepa._transactions:
            CDTTRFTXINF = ET.SubElement(PMTINF, 'CdtTrfTxInf')
            CDT_PMTID = ET.SubElement(CDTTRFTXINF, 'PmtId')
            if tx._cdt_instr_id is not None:
                ET.SubElement(CDT_PMTID, 'InstrId').text = tx._cdt_instr_id
            ET.SubElement(CDT_PMTID, 'EndToEndId').text = tx._cdt_end_to_end_id
            if tx._cdt_instr_prty is not None:
                CDT_PMTTPINF = ET.SubElement(CDTTRFTXINF, 'PmtTpInf')
                ET.SubElement(CDT_PMTTPINF, 'InstrPrty').text = tx._cdt_instr_prty
            CDT_AMT = ET.SubElement(CDTTRFTXINF, 'Amt')
            ET.SubElement(CDT_AMT, 'InstdAmt', Ccy=tx._cdt_instd_amt_curr).text = str(tx._cdt_instd_amt)
            CDT_CDTRAGT = ET.SubElement(CDTTRFTXINF, 'CdtrAgt')
            CDT_FININSTNID = ET.SubElement(CDT_CDTRAGT, 'FinInstnId')
            ET.SubElement(CDT_FININSTNID, 'BIC').text = tx._cdt_bic

            CDT_CDTR = ET.SubElement(CDTTRFTXINF, 'Cdtr')
            ET.SubElement(CDT_CDTR, 'Nm').text = tx._payment_receiver._name

            if len(tx._payment_receiver._address_lines) > 0:

                CDT_PSTLADR = ET.SubElement(CDT_CDTR, 'PstlAdr')

                for x in tx._payment_receiver._address_lines:
                    ET.SubElement(CDT_PSTLADR, 'AdrLine').text = x

                CDT_CTRY = ET.SubElement(CDT_PSTLADR, 'Ctry')
                CDT_CTRY.text = tx._payment_receiver._country

            """
            Specification "OP-POHJOLA-RYHMaN C2B-PALVELUT Maksuliikepalvelut" in
            page 17 defines, that the IBAN (CDT_IBAN variable) should be located
            directly as a text in 'CdtrAcct'-element, but this doesn't pass the
            validation
            """
            CDT_CDTRACCT = ET.SubElement(CDTTRFTXINF, 'CdtrAcct')
            CDT_CDTRACCT_ID = ET.SubElement(CDT_CDTRACCT, 'Id')
            ET.SubElement(CDT_CDTRACCT_ID, 'IBAN').text = tx._cdt_cdtr_acct

            if tx._pmt_purp is not None:
                CDT_PURP = ET.SubElement(CDTTRFTXINF, 'Purp')
                ET.SubElement(CDT_PURP, 'Cd').text = tx._pmt_purp

            if tx._cdt_ustrd is not None:
                CDT_RMTINF = ET.SubElement(CDTTRFTXINF, 'RmtInf')
                ET.SubElement(CDT_RMTINF, 'Ustrd').text = tx._cdt_ustrd

    def _construct_xml(self):
        """
        Stiches together the given information to form the XML
        """
        # Calculate the total amount of payments
        sum_of_transactions = Decimal('0.0')
        nb_of_txs = 0
        for payment in self._payments:
            for transaction in payment._transactions:
                sum_of_transactions += Decimal(str(transaction._cdt_instd_amt))
                nb_of_txs += 1

        # Construct the group header to XML-format
        self._group_header_to_xml(self._msg_id, nb_of_txs, self._grpg,
                                  sum_of_transactions)

        # Add all payments from the list to XML
        for payment in self._payments:
            self._add_SEPA_payment_to_xml(payment)

    def __str__(self):
        """
        Returns string representation of the C2B-message

        @rtype: C{string}
        @return: Object information in validated XML-string

        @raise IOError: If the schema-file is missing
        @raise ValidationError: If the document doesn't comply with the schema
        """

        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "resources/pain.001.001.02.xsd"
                                )
            with open(path, 'rb') as f:
                schema = f.read()
        except IOError as e:
            print(e)
            return False

        self._construct_xml()

        xml_string = str(ET.tostring(DOC,
                                 xml_declaration=True,
                                 #pretty_print=True,
                                 encoding='UTF-8'),
                         'UTF-8')

        xml_schema = ET.XMLSchema(ET.XML(schema))
        #print(xml_string)
        if xml_schema.validate(ET.XML(xml_string)):
            return str(xml_string)
        else:
            print(xml_schema.error_log.last_error)
            raise ValidationError('Document validation failed')


class C2BResponse():
    """
    C2BResponse is used to parse the C2b-material response

    @return: Textual composition of the message
    @rtype: string
    """

    def __init__(self, app_response):
        """
        Initializes the parser and parses the response

        @param app_response: XML response from the bank
        @type app_response: string
        """

        self._pain = None
        self._camt = None

        self._parse_response(app_response)

    def _parse_response(self, app_response):
        """
        Parses the XML-response from the bank and creates a response-object
        with a list of transactions of type L{PmntInfAndStatus}.

        @param app_response: XML response from the bank
        @type app_response: string
        """
        ns_pain = '{urn:iso:std:iso:20022:tech:xsd:pain.002.001.02}'
        pain_doc = ns_pain + 'Document'
        pain_xpath = "//*[local-name() = 'Document' and namespace-uri() = '" + ns_pain[1:][:-1] + "']"
        ns_camt = '{urn:iso:std:iso:20022:tech:xsd:camt.054.001.02}'
        camt_doc = ns_camt + 'Document'
        camt_xpath = "//*[local-name() = 'Document' and namespace-uri() = '" + ns_camt[1:][:-1] + "']"
        tree = ET.parse(BytesIO(app_response), ET.XMLParser(ns_clean=True))

        if len(tree.xpath((pain_xpath))) != 0:
            if tree.xpath((pain_xpath))[0].tag == pain_doc:
                self._pain = C2BResponsePain(app_response)
        elif len(tree.xpath((camt_xpath))) != 0:
            if tree.xpath((camt_xpath))[0].tag == camt_doc:
                self._camt = C2BResponseCamt(app_response)

    def get_response(self):
        if self._pain is not None:
            return self._pain
        elif self._camt is not None:
            return self._camt

    def __str__(self):
        if self._pain is not None:
            return str(self._pain)
        elif self._camt is not None:
            return str(self._camt)


class C2BResponsePain():
    """
    Class for the pain-based C2B-response

    @type _response_type: string
    @ivar _response_type: Type of the response
    @type _hdr_msg_id: string
    @ivar _hdr_msg_id: Feedback ID given by the bank
    @type _hdr_cre_dt_tm: string
    @ivar _hdr_cre_dt_tm: Feedback message creation time
    @type _orgnl_msg_id: string
    @ivar _orgnl_msg_id: Message ID from the original payment message
    @type _orgnl_msg_nm_id: string
    @ivar _orgnl_msg_nm_id: Type of the original message
    @type _orgnl_cre_dt_tm: string
    @ivar _orgnl_cre_dt_tm: Timestamp from original message's "CreDtTm"-field
    @type _orgnl_nb_of_txs: string
    @ivar _orgnl_nb_of_txs: Number of transactions in the original message.
    @type _grp_sts: string
    @ivar _grp-sts: The status of the delivered material
    @type _sts_cd: string
    @ivar _sts_cd: Reason code for the material rejection
    @type _addtl_sts_rsn_inf: string
    @ivar _addtl_sts_rsn_inf: Rejection code explanation in plain text
    @type _payment_inf: L{PmntInfAndStatus}
    @ivar _payment_inf: List of PmntInfAndStatus objects holding payment information
    """

    def __init__(self, app_response):
        """
        Initializes the values for the pain-based response
        """
        self._response_type = 'pain'
        self._hdr_msg_id = None
        self._hdr_cre_dt_tm = None
        self._orgnl_msg_id = None
        self._orgnl_msg_nm_id = None
        self._orgnl_cre_dt_tm = None
        self._orgnl_nb_of_txs = None
        self._grp_sts = None
        self._sts_cd = None
        self._addtl_sts_rsn_inf = None
        self._payment_inf = []

        self._parse_response(app_response)

    def _parse_response(self, app_response):
        ns_pain_002 = '{urn:iso:std:iso:20022:tech:xsd:pain.002.001.02}'
        tree = ET.parse(BytesIO(app_response), ET.XMLParser(ns_clean=True))

        for element in tree.iter():
            # Group Header
            if element.tag == ns_pain_002 + 'MsgId':
                self._hdr_msg_id = element.text
            if element.tag == ns_pain_002 + 'CreDtTm':
                self._hdr_cre_dt_tm = element.text

            # Original message information
            if element.tag == ns_pain_002 + 'OrgnlMsgId':
                self._orgnl_msg_id = element.text
            if element.tag == ns_pain_002 + 'OrgnlMsgNmId':
                self._orgnl_msg_nm_id = element.text
            if element.tag == ns_pain_002 + 'OrgnlCreDtTm':
                self._orgnl_cre_dt_tm = element.text
            if element.tag == ns_pain_002 + 'OrgnlNbOfTxs':
                self._orgnl_nb_of_txs = element.text
            if element.tag == ns_pain_002 + 'GrpSts':
                self._grp_sts = element.text

        status_code = tree.xpath(('/ns:Document' +
                                 '/ns:pain.002.001.02' +
                                 '/ns:OrgnlGrpInfAndSts' +
                                 '/ns:StsRsnInf' +
                                 '/ns:StsRsn' +
                                 '/ns:Cd'),
                                namespaces={'ns': ns_pain_002[1:][:-1]})

        status_reason = tree.xpath(('/ns:Document' +
                                    '/ns:pain.002.001.02' +
                                    '/ns:OrgnlGrpInfAndSts' +
                                    '/ns:StsRsnInf' +
                                    '/ns:AddtlStsRsnInf'),
                                   namespaces={'ns': ns_pain_002[1:][:-1]})

        # This is to be used inside the transaction where?
        orgn_pmnt_inf_id = tree.xpath(('/ns:Document' +
                                       '/ns:pain.002.001.02' +
                                       '/ns:TxInfAndSts' +
                                       '/ns:OrgnlEndToEndId'),
                                      namespaces={'ns': ns_pain_002[1:][:-1]})

        if len(status_code) == 1:
            self._sts_cd = status_code[0].text

            if len(status_reason) == 1:
                self._addtl_sts_rsn_inf = status_reason[0].text

        context = ET.iterparse(BytesIO(app_response), events=("start", "end"))
        for action, element in context:
            if (element.tag == ns_pain_002 + 'TxInfAndSts'):
                tx = c2bhelper.PmntInfAndStatus()
                for el in element.iter():
                    if action == 'start':
                        if el.tag == ns_pain_002 + 'OrgnlEndToEndId':
                            tx._orgnl_end_to_end_id = el.text
                        if el.tag == ns_pain_002 + 'OrgnlTxId':
                            tx._orgnl_tx_id = el.text
                        if el.tag == ns_pain_002 + 'TxSts':
                            tx._tx_sts = el.text
                        if el.tag == ns_pain_002 + 'Cd':
                            tx._sts_cd = el.text
                        if el.tag == ns_pain_002 + 'AddtlStsRsnInf':
                            tx._sts_addtl_sts_rns_inf = el.text
                        if el.tag == ns_pain_002 + 'InstdAmt':
                            tx._instd_amt = el.text
                            tx._instd_amt_curr = el.get('Ccy')
                        if el.tag == ns_pain_002 + 'ReqdExctnDt':
                            tx._reqd_exctn_dt = el.text
                        if el.tag == ns_pain_002 + 'DbtrAcct':
                            for e in el.iter():
                                if e.tag == ns_pain_002 + 'IBAN':
                                    tx._dbtr_iban = e.text
                                if e.tag == ns_pain_002 + 'BBAN':
                                    tx._dbtr_bban = e.text
                                if e.tag == ns_pain_002 + 'PrtryAcct':
                                    if e[0].tag == ns_pain_002 + 'Id':
                                        tx._dbtr_prtry_acct_id = e[0].text
                        if el.tag == ns_pain_002 + 'CdtrAcct':
                            for e in el.iter():
                                if e.tag == ns_pain_002 + 'IBAN':
                                    tx._cdtr_iban = e.text
                                if e.tag == ns_pain_002 + 'BBAN':
                                    tx._dbtr_bban = e.text
                                if e.tag == ns_pain_002 + 'PrtryAcct':
                                    if e[0].tag == ns_pain_002 + 'Id':
                                        tx._cdtr_prtry_acct_id = e[0].text

                self._payment_inf.append(tx)

    def get_group_status(self):
        """
        @return: Group status for the response
        @rtype: string
        """
        return(self._grp_sts)

    def get_payments(self):
        """
        @return: List of payment feedback in a message
        @rtype: list of L{PmntInfAndStatus}
        """
        return(self._payment_inf)

    def __str__(self):

        return_string = ''.join(["{0}: {1}\n".format(key.title().replace('_',''), value) for key, value in self.__dict__.items() if value is not None]) + '\n'

        for x in self._payment_inf:
            return_string += str(x)

        return(return_string)


class C2BResponseCamt():
    """
    Class for the camt-based response

    Supports response for only one bank account

    @type _response_type: string
    @ivar _response_type: Type of the response
    @type _hdr_msg_id: string
    @ivar _hdr_msg_id: Response ID given by the bank
    @type _hdr_cre_dt_tm: string
    @ivar _hdr_cre_dt_tm: Response message creation time
    @type _hdr_id: string
    @ivar _hdr_id: Response receiver's identification
    @type _hdr_cd: string
    @ivar _hdr_cd: Bank's identification
    @type _ntfctn_id: string
    @ivar _ntfctn_id: Notification ID
    @type _ntfctn_cre_dt_tm: string
    @ivar _ntfctn_cre_dt_tm: Notification creation time
    @type _acct_iban: string
    @ivar _acct_iban: Payer's IBAN number
    @type _ntry_amt: string
    @ivar _ntry_amt: The sum of handled transactions
    @type _ntry_amt_curr: string
    @ivar _ntry_amt_curr: The currency of transactions (defaults to XXX with OP)
    @type _ntry_cdt_dbt_ind: string
    @ivar _ntry_cdt_dbt_ind: Credit/Debit indicator
    @type _ntry_sts: string
    @ivar _ntry_sts: The status of entries taken to response is always 'BOOK'
    @type _ntry_bookg_dt: string
    @ivar _ntry_bookg_dt: Date of payment
    @type _ntry_acct_svcr_ref: string
    @ivar _ntry_acct_svcr_ref: Archiving code that matches account statement entry
    @type _ntry_bk_tx_cd_prtry_cd: string
    @ivar _ntry_bk_tx_cd_prtry_cd: Bank transactin code
    @type _ntry_dtls_btch_pmt_inf_id: string
    @ivar _ntry_dtls_btch_pmt_inf_id: Payment information identification from the original pain message

    @note: Testing has not been done, because the test environment doesn't provide these reports.
    """

    def __init__(self, app_response):

        self._response_type = 'camt'
        self._hdr_msg_id = None
        self._hdr_cre_dt_tm = None
        self._hdr_id = None
        self._hdr_cd = None
        self._ntfctn_id = None
        self._ntfctn_cre_dt_tm = None
        self._acct_iban = None
        self._ntry_amt = None
        self._ntry_amt_curr = None
        self._ntry_cdt_dbt_ind = None
        self._ntry_sts = None
        self._ntry_bookg_dt = None
        self._ntry_acct_svcr_ref = None
        self._ntry_bk_tx_cd_prtry_cd = None
        self._ntry_dtls_btch_pmt_inf_id = None

        self._transactin_details = []
        self._parse_response(app_response)

    """
    def _parse_response(self, app_response):
        namespace = '{urn:iso:std:iso:20022:tech:xsd:camt.054.001.02}'
        #tree = ET.parse(BytesIO(app_response), ET.XMLParser(ns_clean=True))

        context = ET.iterparse(BytesIO(app_response), events=("start", "end"))
        for action, element in context:
            #print('%s: %s' % (action, element))
            if (action, element.tag) == ('start', namespace + 'GrpHdr'):
                #print('%s: %s' % (action, element))
                for el in element.iter():
                    if el.tag == namespace + 'MsgId':
                        self._hdr_msg_if = el.text
                    if el.tag == namespace + 'CreDtTm':
                        self._hdr_cre_dt_tm = el.text
                    if el.tag == namespace + 'Id':
                        self._hdr_id = el.text
                    if el.tag == namespace + 'Cd':
                        self._hdr_cd = el.text
                    if el.tag == namespace + 'AddtlInf':
                        self._hdr_addtl_inf = el.text

            if (action, element.tag) == ('start', namespace + 'Ntfctn'):
                self._ntfctn_id = element.xpath('/ns:Document' +
                                                '/ns:BkToCstmrDbtCdtNtfctn' +
                                                '/ns:Ntfctn' +
                                                '/ns:Id',
                                                namespaces={'ns': namespace[1:][:-1]})[0].text
                self._ntfctn_cre_dt_tm = element.xpath('/ns:Document' +
                                                       '/ns:BkToCstmrDbtCdtNtfctn' +
                                                       '/ns:Ntfctn' +
                                                       '/ns:CreDtTm',
                                                       namespaces={'ns': namespace[1:][:-1]})[0].text

            if element.tag == namespace + 'Acct':
                for el in element.iter():
                    if el.tag == namespace + 'IBAN':
                        self._acct_iban = el.text

            if  element.tag == namespace + 'Ntry':
                for el in element.iter():
                    if action == 'start':
                        if el.tag == namespace + 'Amt':
                            self._ntry_amt = el.text
                            self._ntry_amt_curr = el.get('Ccy')
                        if el.tag == namespace + 'CdtDbtInd':
                            self._ntry_cdt_dbt_ind = el.text
                        if el.tag == namespace + 'Sts':
                            self._ntry_sts = el.text
                        if el.tag == namespace + 'BookgDt':
                            for e in el.iter():
                                if e.tag == namespace + 'Dt':
                                    self._ntry_bookg_dt = e.text
                        if el.tag == namespace + 'AcctSvcrRef':
                            self._ntry_acct_svcr_ref = el.text
                        if el.tag == namespace + 'BkTxCd':
                            for e in el.iter():
                                if e.tag == namespace + 'Prtry':
                                    for ee in e.iter():
                                        if ee.tag == namespace + 'Cd':
                                            self._ntry_bk_tx_cd_prtry_cd = ee.text
                        if el.tag == namespace + 'NtryDtls':
                            for e in el.iter():
                                if e.tag == namespace + 'Btch':
                                    for ee in e.iter():
                                        if ee.tag == namespace + 'PmtInfId':
                                            self._ntry_dtls_btch_pmt_inf_id = ee.text
                                        if ee.tag == namespace + 'NbOfTxs':
                                            self._ntry_dtls_btch_nb_of_txs = ee.text
                                if e.tag == namespace + 'TxDtls':
                                    tx = c2bhelper.TxDtls()
                                    for ee in e.iter():
                                        if ee.tag == namespace + 'AcctSvcrRef':
                                            tx._acct_svcr_ref = ee.text
                                        if ee.tag == namespace + 'InstrId':
                                            tx._instr_id = ee.text
                                        if ee.tag == namespace + 'EndToEndId':
                                            tx._end_to_end_id = ee.text
                                        if ee.tag == namespace + 'AmtDtls':
                                            for eee in ee.iter():
                                                if eee.tag == namespace + 'InstdAmt':
                                                    for eeee in eee.iter():
                                                        if eeee.tag == namespace + 'Amt':
                                                            tx._instd_amt = eeee.text
                                                            tx._instd_amt_curr = eeee.get('Ccy')
                                                        if eeee.tag == namespace + 'CcyXchg':
                                                            for eeeee in eee.iter():
                                                                if eeeee.tag == namespace + 'TrgtCcy':
                                                                    tx._instd_ccy_xchg_target_ccy = eeeee.text
                                                                if eeeee.tag == namespace + 'UnitCcy':
                                                                    tx._instd_ccy_xchg_unit_ccy = eeeee.text
                                                                if eeeee.tag == namespace + 'XchgRate':
                                                                    tx._instd_ccy_xchg_rate = eeeee.text
                                                                if eeeee.tag == namespace + 'CtrctId':
                                                                    tx._instd_ccy_xchg_ctrct_id = eeeee.text
                                                                if eeeee.tag == namespace + 'QtnDt':
                                                                    tx._instd_ccy_xchg_qtn_dt = eeeee.text
                                                if eee.tag == namespace + 'CntrValAmt':
                                                    for eeee in eee.iter():
                                                        if eeee.tag == namespace + 'Amt':
                                                            tx._cntr_val_amt = eeee.text
                                        if ee.tag == namespace + 'Chrgs':
                                            for eee in ee.iter():
                                                if eee.tag == namespace + 'Br':
                                                    tx._tx_chargers_bearer.append(eee.text)
                                        if ee.tag == namespace + 'RltdPties':
                                            #print("%s, %s" % (action, ee))
                                            for eee in ee.iter():
                                                if eee.tag == namespace + 'Dbtr':
                                                    for eeee in eee.iter():
                                                        if eeee.tag == namespace + 'Nm':
                                                            tx._dbtr_nm = eeee.text
                                                        if eeee.tag == namespace + 'Id':
                                                            for eeeee in eeee.iter():
                                                                if eeeee.tag == namespace + 'OrgId':
                                                                    for eeeeee in eeeee.iter():
                                                                        if eeeeee.tag == namespace + 'Othr':
                                                                            for eeeeeee in eeeeee.iter():
                                                                                if eeeeeee.tag == namespace + 'Id':
                                                                                    tx._dbtr_id.append(eeeeeee.text)
                                                if eee.tag == namespace + 'UltmtDbtr':
                                                    for eeee in eee.iter():
                                                        if eeee.tag == namespace + 'Nm':
                                                            tx._ultmt_dbtr_nm = eeee.text
                                                if eee.tag == namespace + 'Cdtr':
                                                    for eeee in eee.iter():
                                                        if eeee.tag == namespace + 'Nm':
                                                            tx._cdtr_nm = eeee.text
                                                        if eeee.tag == namespace + 'PstlAdr':
                                                            for eeeee in eeee.iter():
                                                                if eeeee.tag == namespace + 'AdrLine':
                                                                    tx._cdtr_adr_lines.append(eeeee.text)
                                                        if eeee.tag == namespace + 'Id':
                                                            for eeeee in eeee.iter():
                                                                if eeeee.tag == namespace + 'OrgId':
                                                                    for eeeeee in eeeee.iter():
                                                                        if eeeeee.tag == namespace + 'BICOrBEI':
                                                                            tx._cdtr_id_bic_or_bei = eeeeee.text
                                                                        if eeeeee.tag == namespace + 'Othr':
                                                                            for eeeeeee in eeeeee.iter():
                                                                                if eeeeeee.tag == namespace + 'Id':
                                                                                    tx._cdtr_id_org_othr_id = eeeeeee.text
                                                                if eeeee.tag == namespace + 'PrvtId':
                                                                    for eeeeee in eeeee.iter():
                                                                        if eeeeee.tag == namespace + 'Othr':
                                                                            for eeeeeee in eeeeee.iter():
                                                                                if eeeeeee.tag == namespace + 'Id':
                                                                                    tx._cdtr_id_prvt_othr_id = eeeeeee.text
                                                if eee.tag == namespace + 'CdtrAcct':
                                                    for eeee in eee.iter():
                                                        if eeee.tag == namespace + 'Id':
                                                            for eeeee in eeee.iter():
                                                                if eeeee.tag == namespace + 'IBAN':
                                                                    tx._cdtr_acct_id_iban = eeeee.text
                                                                if eeeee.tag == namespace + 'Othr':
                                                                    for eeeeee in eeeee.iter():
                                                                        if eeeeee.tag == namespace + 'Id':
                                                                            tx._cdtr_acct_id_othr_id = eeeeee.text
                                                if eee.tag == namespace + 'UltmtCdtr':
                                                    for eeee in eee.iter():
                                                        if eeee.tag == namespace + 'Nm':
                                                            tx._ultmt_cdtr_nm = eeee.text
                                            if ee.tag == namespace + 'RltdAgts':
                                                for eee in ee.iter():
                                                    if eee.tag == namespace + 'CdtrAgt':
                                                        for eeee in eee.iter():
                                                            if eeee.tag == namespace + 'FinInstnId':
                                                                for eeeee in eeee.iter():
                                                                    if eeeee.tag == namespace + 'BIC':
                                                                        tx._rltd_agts_cdtr_agt_bic = eeeee.text
                                                                    if eeeee.tag == namespace + 'ClrSysMmbId':
                                                                        for eeeeee in eeeeee.iter():
                                                                            if eeeeee.tag == namespace + 'ClrSysId':
                                                                                for eeeeeee in eeeeee.iter():
                                                                                    if eeeeeee.tag == namespace + 'Cd':
                                                                                        tx._rltd_agts_cdtr_agt_clr_sys_id = eeeeeee.text
                                                                    if eeeee.tag == namespace + 'Nm':
                                                                        tx._rltd_agts_cdtr_agt_nm = eeeee.text
                                                                    if eeeee.tag == namespace + 'PstlAdr':
                                                                        for eeeeee in eeeee.iter():
                                                                            if eeeeee.tag == namespace + 'AdrLine':
                                                                                tx._rltd_agts_cdtr_agt_adr_lines.append(eeeeee.text)
                                                    if eee.tag == namespace + 'IntrmyAgt1':
                                                        for eeee in eee.iter():
                                                            if eeee.tag == namespace + 'FinInstnId':
                                                                for eeeee in eeee.iter():
                                                                    if eeeee.tag == namespace + 'BIC':
                                                                        tx._intrmy_agt1_bic = eeeee.text
                                                                    if eeeee.tag == namespace + 'ClrSysMmbId':
                                                                        for eeeeee in eeeeee.iter():
                                                                            if eeeeee.tag == namespace + 'ClrSysId':
                                                                                for eeeeeee in eeeeee.iter():
                                                                                    if eeeeeee.tag == namespace + 'Cd':
                                                                                        tx._intrmy_agt1_clr_sys_id = eeeeeee.text
                                                                    if eeeee.tag == namespace + 'Nm':
                                                                        tx._rltd_agts_cdtr_agt_nm = eeeee.text
                                                                    if eeeee.tag == namespace + 'PstlAdr':
                                                                        for eeeeee in eeeee.iter():
                                                                            if eeeeee.tag == namespace + 'AdrLine':
                                                                                tx._intrmy_agt1_adr_lines.append(eeeeee.text)
                                            if ee.tag == namespace + 'Purp':
                                                for eee in ee.iter():
                                                    if eee.tag == namespace + 'Cd':
                                                        tx._purpose = eee.text
                                            if ee.tag == namespace + 'RmtInf':
                                                for eee in ee.iter():
                                                    if eee.tag == namespace + 'Ustrd':
                                                        tx._rmt_inf_ustrd = eee.text
                                                    if eee.tag == namespace + 'Strd':
                                                        rmt = c2bhelper.RmtInfStrd()
                                                        for eeee in eee.iter():
                                                            if eeee.tag == namespace + 'RfrdDocInf':
                                                                for eeeee in eeee.iter():
                                                                    if eeeee.tag == namespace + 'Tp':
                                                                        for eeeeee in eeeee.iter():
                                                                            if eeeeee.tag == namespace + 'CdOrPrtry':
                                                                                for eeeeeee in eeeeee.iter():
                                                                                    if eeeeeee.tag == namespace + 'Cd':
                                                                                        rmt._rfrd_doc_inf_cd_or_prtry = eeeeeee.text
                                                            if eeee.tag == namespace + 'RfrdDocAmt':
                                                                for eeeee in eeee.iter():
                                                                    if eeeee.tag == namespace + 'CdtNoteAmt':
                                                                        rmt._rfrd_doc_amt_cdt_note_amt = eeeee.text
                                                                    if eeeee.tag == namespace + 'RmtdAmt':
                                                                        rmt._rfrd_doc_amt_rmtd_amt = eeeee.text
                                                            if eeee.tag == namespace + 'CdtrRefInf':
                                                                for eeeee in eeee.iter():
                                                                    if eeeee.tag == namespace + 'Tp':
                                                                        for eeeeee in eeeee.iter():
                                                                            if eeeeee.tag == namespace + 'CdOrPrtry':
                                                                                for eeeeeee in eeeeee.iter():
                                                                                    if eeeeeee.tag == namespace + 'Cd':
                                                                                        rmt._cdtr_ref_inf_cd_or_prtry_cd = eeeeeee.text
                                                                            if eeeeee.tag == namespace + 'Issr':
                                                                                rmt._cdtr_ref_inf_tp_issr = eeeeee.text
                                                                    if eeeee.tag == namespace + 'Ref':
                                                                        rmt._cdtr_ref_inf_ref = eeeee.text
                                                            if eeee.tag == namespace + 'AddtlRntInf':
                                                                rmt._addtl_rnt_inf = eeee.text
                                                        tx._rmt_inf_strd_list.append(rmt)
                                            if ee.tag == namespace + 'RltdDts':
                                                for eee in ee.iter():
                                                    if eee.tag == namespace + 'AccptncDtTm':
                                                        tx._rltd_dts_accptnc_dt_tm = eee.text
                                                    if eee.tag == namespace + 'IntrBkSttlmDt':
                                                        tx._rltd_dts_intr_bk_sttlm_dt = eee.text
    """


class NotEnoughParametersError(Exception):

    def __init__(self, value):
        self._value = value

    def __str__(self):
        return repr(self._value)


class ValidationError(Exception):

    def __init__(self, value):
        self._value = value

    def __str__(self):
        return repr(self._value)
