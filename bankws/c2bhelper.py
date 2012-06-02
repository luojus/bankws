class SEPA():
    """
    SEPA class is used to construct the individual payment to the material

    @ivar _payer: REQ Company information for the payment
    @type _payer: L{Entity}

    @ivar _pmt_mtd: REQ Payment method, TRF in SEPA-payments
    @type _pmt_mtd: string
    @ivar _cd: REQ Must be SEPA in SEPA-payments
    @type _cd: string
    @ivar _reqd_exctn_dt: REQ Requested expiration date
    @type _reqd_exctn_dt: string
    @ivar _material_id: REQ "Maksatustunnus" from the debtor's C2B-contract
    @type _material_id: string
    @ivar _iban: REQ Account number for the debtor
    @type _iban: string
    @ivar _bic: REQ BIC for the debtor's bank
    @type _bic: string
    @ivar _chrg_br: "Kulukoodi", SLEV in SEPA-payments
    @type _chrg_br: string
    @ivar _payment_information_id: Identification for the instalment (RECOMMENDED)
    @type _payment_information_id: string
    @ivar _instr_prty: Code for payment urgency
    @type _instr_prty: string
    @ivar _ccy: Payment currency
    @type _ccy: string
    @ivar _ultmt_dbtr: Ultimate debtor of the payment
    @type _ultmt_dbtr: string

    @ivar _transactions: List of transactions in the payment
    @type _transactions: L{CdtTrfTxInf}

    @note: Required attributes are indicated with REQ.
    @note: Only SEPA payment and salary inside Finland are available
    """
    def __init__(self, payer, pmt_mtd, cd,
                 reqd_exctn_dt, material_id, iban, bic, chrg_br,
                 # additional parameters (not required)
                 pmt_inf_id=None, instr_prty=None, ccy=None, ultmt_dbtr=None):
        """
        Constructs the new SEPA-payment.

        @raise TypeError: If not enough parameters are given
        @raise ValueError: If checked parameters are not acceptable

        @note: With an optional (OPT) parameters, use "None" if not giving other values
        """
        self._payer = payer

        if pmt_mtd in ['TRF', 'CHK', 'TRA']:
            self._pmt_mtd = pmt_mtd
        else:
            raise ValueError('pmt_mtd must be [TRF, CHK, TRA], where TRF is required in SEPA-payment')

        if cd in ['SEPA', 'SDVA', 'PRPT']:
            self._cd = cd
        else:
            raise ValueError('cd (Service level code) must be [SEPA, SDVA, PRPT]')

        self._reqd_exctn_dt = reqd_exctn_dt

        self._material_id = material_id
        self._iban = iban
        self._bic = bic
        self._chrg_br = chrg_br
        self._payment_information_id = pmt_inf_id
        self._instr_prty = instr_prty
        self._ccy = ccy
        self._ultmt_dbtr = ultmt_dbtr

        self._transactions = []

    def add_transaction(self, tr):
        """
        Adds the credit transfer transaction information to the payment

        @param tr: Transaction information
        @type tr: L{CdtTrfTxInf}
        """
        self._transactions.append(tr)


class CdtTrfTxInf():
    """
    Class for Credit Transfer Transaction Information

    @ivar _payment_receiver: Information about the payment receiver
    @type _payment_receiver: L{Entity}
    @ivar _pmt_purp: Payment purpose, one of [STDY, BECH, PENS, BENE, SSBE,
        AGRT, SALA, TAXS] or 'None' if not eligible
    @type _pmt_purp: string
    @ivar _cdt_end_to_end_id: Unique ID for the transaction
    @type _cdt_end_to_end_if: string
    @ivar _cdt_instd_amt: Amount of the payment
    @type _cdt_instd_amd: float
    @ivar _cdt_instd_amt_curr: Currency of the payment
    @type _cdt_instd_amt_curr: string
    @ivar _cdt_bic: BIC for the payment receiver's bank
    @type _cdt_bic: string
    @ivar _cdt_cdtr_acct: Creditor's bank account number in IBAN-format
    @type _cdt_cdtr_acct: string
    @ivar _chrg_br: "Kulukoodi", must be SLEV in SEPA-payments
    @type _chrg_br: string
    @ivar _cdt_instr_id: Delivered to creditor's account statement
    @type _cdt_instr_id: string
    @ivar _cdt_instr_prty: Value for the transaction urgency [NORM, HIGH]
    @type _cdt_instr_prty: string
    @ivar _cdt_scl_scty_nb: Social security number for the salary receiver
    @type _cdt_scl_scty_nb: string
    @ivar _cdt_ustrd: Free-text message for the payment receiver
    @type _cdt_ustrd: string
    @ivar _cdt_ultmt_cdr: Ultimate creditor
    @type _cdt_ultmt_cdr: string
    """

    def __init__(self, receiver, pmt_purp, end_to_end_id, instd_amt,
                 instd_amt_curr, cdtr_bic, cdtr_acct, chrg_br=None,
                 instr_id=None, instr_prty=None,
                 scl_scty_nb=None, ustrd=None, ultmt_cdr=None):
        """
        @type receiver: L{Entity}
        @param receiver: Payment receiver
        @type pmt_purp: string
        @param pmt_purp: REQ Payment purpose, one of [STDY, BECH, PENS, BENE, SSBE,
            AGRT, SALA, TAXS] or 'None' if not eligible
        @type end_to_end_id: string
        @param end_to_end_id: REQ Required ID provided by the payment initiator,
            which uniquely identifies the transaction
        @type instd_amt: string
        @param instd_amt: REQ Amount of the transaction
        @type instd_amt_curr: string
        @param instd_amt_cyrr: REQ Transaction currency [EUR, USD, etc]
        @type cdtr_bic: string
        @param cdtr_bic: REQ Creditors bank's BIC code
        @type cdtr_acct: string
        @param cdtr_acct: REQ Creditor's bank account number in IBAN-format
        @type chrg_br: string
        @param chrg_br: REQ "Kulukoodi", must be SLEV in SEPA-payments
        @type instr_id: string
        @param instr_id: OPT Transaction ID, which is displayed on debtor's own
            account statement
        @type instr_prty: string
        @param instr_prty: OPT Classification for the transaction urgency,
            accepted values are NORM or HIGH
        @type sc_scty_nb: string
        @param sc_scty_nb: Social security number for the person receiving salary
        @type ustrd: string
        @param ustrd: OPT Free-text message for the transaction receiver
        @type ultmt_cdr: string
        @param ultmt_cdr: OPT Ultimate creditor

        @raise ValueError: If some values of the parameters are not accepted

        @note: With an optional (OPT) parameters, use "None" if not giving other values
        """

        # Mandatory
        self._payment_receiver = receiver
        self._pmt_purp = pmt_purp
        self._cdt_end_to_end_id = end_to_end_id
        self._cdt_instd_amt = instd_amt
        self._cdt_instd_amt_curr = instd_amt_curr
        self._cdt_bic = cdtr_bic
        self._cdt_cdtr_acct = cdtr_acct

        if instr_prty is not None:
            if instr_prty in ['NORM', 'HIGH']: self._cdt_instr_prty = instr_prty
            else: raise ValueError('instr_prty value is not accepted')
        else: self._cdt_instr_prty = None
        
        # Optional
        self._chrg_br = chrg_br
        self._cdt_instr_id = instr_id
        self._cdt_ultmt_cdr = ultmt_cdr
        self._cdt_scl_scty_nb = scl_scty_nb
        self._cdt_ustrd = ustrd


class PmntInfAndStatus():
    """
    PmntInfAndStatus class is used to represent the information on an
    individual payment

    @type _orgnl_instr_id: string
    @ivar _orgnl_instr_id: Unique identifier given by the client, taken from
                           the original message's InstrId-field
    @type _orgnl_end_to_end_id: string
    @ivar _orgnl_end_to_end_id: End to end id from the original pain-message
    @type _orgnl_tx_id: string
    @ivar _orgnl_tx_id: Archiving identifier
    @type _tx_sts: string
    @ivar _tx_sts: Status of the transaction
    @type _sts_cd: string
    @ivar _sts_cd: Reason code for the transaction rejection
    @type _sts_addtl_sts_rsn_inf: string
    @ivar _sts_addtl_sts_rsn_inf: Additional cleartext information about the reason
    @type _instd_amt: string
    @ivar _instd_amt: Total amount of the transaction
    @type _instd_amt_curr: string
    @ivar _instd_amt_curr: Transaction currency
    @type _reqd_exctn_dt: string
    @ivar _reqd_exctn_dt: Transaction expiration date
    @type _dbtr_iban: string
    @ivar _dbtr_iban: IBAN-account number for the transaction payer
    @type _dbtr_bban: string
    @ivar _dbtr_bban: BBAN-account number for the transaction payer
    @type _dbtr_prtry_acct_id: string
    @ivar _dbtr_prtry_acct_id: Additional account number for the payer
    @type _cdtr_iban: string
    @ivar _cdtr_iban: IBAN-account number for the transaction receiver
    @type _cdtr_bban: string
    @ivar _cdtr_bban: BBAN-account number for the transaction receiver
    @type _cdtr_prtry_acct_id: string
    @ivar _cdtr_prtry_acct_id: Additional account number for the receiver
    """

    def __init__(self):
        self._orgnl_instr_id = None
        self._orgnl_end_to_end_id = None
        self._orgnl_tx_id = None
        self._tx_sts = None
        self._sts_cd = None
        self._sts_addtl_sts_rns_inf = None
        self._instd_amt = None
        self._instd_amt_curr = None
        self._reqd_exctn_dt = None
        self._dbtr_iban = None
        self._dbtr_bban = None
        self._dbtr_prtry_acct_id = None
        self._cdtr_iban = None
        self._cdtr_bban = None
        self._cdtr_prtry_acct_id = None

    def __str__(self):
        """
        String representation of an individual payment feedback

        @return: Textual summary of the payment
        @rtype: string
        """

        return_string = ''.join(["{0}: {1}\n".format(key.title().replace('_',''), value) for key, value in self.__dict__.items() if value is not None]) + '\n'

        return(return_string)


class TxDtls():
    """
    TxDtls class is used to represent the information on an individual payment
    feedback from the camt-response

    @type _acct_svcr_ref: string
    @ivar _acct_svcr_ref: Archiving code for the transaction level
    @type _instr_id: string
    @ivar _instr_id: Value from the original pain message's InstrId-field
    @type _end_to_end_id: string
    @ivar _end_to_end_id: Valus of the EndToEndId-field in original pain message
    @type _instd_amt: string
    @ivar _instd_amt: Amount of the payment
    @type _instd_amt_curr: string
    @ivar _instd_amt_curr: Payment currency
    @type _instd_ccy_xchg_target_ccy: string
    @ivar _instd_ccy_xchg_target_ccy: Payment account currency
    @type _instd_ccy_xchg_unit_ccy: string
    @ivar _instd_ccy_xchg_unit_ccy: Transaction currency
    @type _instd_ccy_xchg_rate: string
    @ivar _instd_ccy_xchg_rate: Exchange rate
    @type _instd_ccy_xchg_ctrct_id: string
    @ivar _instd_ccy_xchg_ctrct_id: Contract Identification
    @type _instd_ccy_xchg_qtn_dt: string
    @ivar _instd_ccy_xchg_qtn_dt: Quatation date for the rate exchange
    @type _cntr_val_amt: string
    @ivar _cntr_val_amt: Counter value on EUR
    @type _tx_chargers_bearer: string
    @ivar _tx_chargers_bearer: List of transaction bearers
    @type _dbtr_id: string
    @ivar _dbtr_id: List of debtor's organization identifications
    @type _ultmt_dbtr_nm: string
    @ivar _ultmt_dbtr_nm: Ultimate debtor name
    @type _cdtr_adr_lines: string
    @ivar _cdtr_adr_lines: List of creditor address lines
    @type _cdtr_id_bic_or_bei: string
    @ivar _cdtr_id_bic_or_bei: BIC or BEI ID
    @type _cdtr_id_org_othr_id: string
    @ivar _cdtr_id_org_othr_id: Creditor's ID for company customers
    @type _cdtr_id_prvt_othr_id: string
    @ivar _cdtr_id_prvt_othr_id: Creditor's ID for private customers
    @type _cdtr_acct_id_iban: string
    @ivar _cdtr_acct_id_iban: Creditor's account IBAN ID
    @type _cdtr_acct_id_othr_id: string
    @ivar _cdtr_acct_id_othr_id: Creditor's account other ID
    @type _ultmt_cdtr_nm: string
    @ivar _ultmt_cdtr_nm: Name of the ultimate creditor
    @type _rltd_agts_cdtr_agt_bic: string
    @ivar _rltd_agts_cdtr_agt_bic: Creditor's bank's BIC
    @type _rltd_agts_cdtr_agt_clr_sys_id: string
    @ivar _rltd_agts_cdtr_agt_clr_sys_id: Creditor's bank's clearing system code
    @type _rltd_agts_cdtr_agt_nm: string
    @ivar _rltd_agts_cdtr_agt_nm: Creditor's bank's name
    @type _rltd_agts_cdtr_agt_adr_lines: string
    @ivar _rltd_agts_cdtr_agt_adr_lines: List of creditor's agent's address lines
    @type _intrmy_agt1_bic: string
    @ivar _intrmy_agt1_bic: Intermediary agent's BIC
    @type _intrmy_agt1_clr_sys_id: string
    @ivar _intrmy_agt1_clr_sys_id: Intermediary agent's clearing system code
    @type _intrmy_agt1_adr_lines: string
    @ivar _intrmy_agt1_adr_lines: List of intermediary agent's address lines
    @type _purpose: string
    @ivar _purpose: Additional information about the payment from debtor
    @type _rmt_inf_ustrd: string
    @ivar _rmt_inf_ustrd: Free-text message for the creditor
    @type _rmt_inf_strd_list: L{RmtInfStrd}
    @ivar _rmt_inf_strd_list: List of structured remittance information in document
    @type _rltd_dts_accptnc_dt_tm: string
    @ivar _rltd_dts_accptnc_dt_tm: Transaction specific payment date
    @type _rltd_dts_intr_bk_sttlm_dt: string
    @ivar _rltd_dts_intr_bk_sttlm_dt: Foreign value date
    """
    def __init__(self):
        self._acct_svcr_ref = None
        self._instr_id = None
        self._end_to_end_id = None
        self._instd_amt = None
        self._instd_amt_curr = None
        self._instd_ccy_xchg_target_ccy = None
        self._instd_ccy_xchg_unit_ccy = None
        self._instd_ccy_xchg_rate = None
        self._instd_ccy_xchg_ctrct_id = None
        self._instd_ccy_xchg_qtn_dt = None
        self._cntr_val_amt = None
        self._ultmt_dbtr_nm = None
        self._cdtr_id_bic_or_bei = None
        self._cdtr_id_org_othr_id = None
        self._cdtr_id_prvt_othr_id = None
        self._cdtr_acct_id_iban = None
        self._cdtr_acct_id_othr_id = None
        self._ultmt_cdtr_nm = None
        self._rltd_agts_cdtr_agt_bic = None
        self._rltd_agts_cdtr_agt_clr_sys_id = None
        self._rltd_agts_cdtr_agt_nm = None
        self._intrmy_agt1_bic = None
        self._intrmy_agt1_clr_sys_id = None
        self._purpose = None
        self._rmt_inf_ustrd = None
        self._rltd_dts_accptnc_dt_tm = None
        self._rltd_dts_intr_bk_sttlm_dt = None

        self._tx_chargers_bearer = []
        self._dbtr_id = []
        self._cdtr_adr_lines = []
        self._rltd_agts_cdtr_agt_adr_lines = []
        self._intrmy_agt1_adr_lines = []
        self._rmt_inf_strd_list = []


class RmtInfStrd():
    """
    RmtInfStrd class is used to represent the information on an individual
    remittance structured message

    @type _rfrd_doc_inf_cd_or_prtry: string
    @ivar _rfrd_doc_inf_cd_or_prtry: RfrdDocInf/RfrdDocTp/CD-information from the pain message
    @type _rfrd_doc_amt_cdt_note_amt: string
    @ivar _rfrd_doc_amt_cdt_note_amt: Value of the CdtNoteAmt-field from the pain message
    @type _rfrd_doc_amt_rmtd_amt: string
    @ivar _rfrd_doc_amt_rmtd_amt: Value of the RmtdAmt-field from the pain message
    @type _cdtr_ref_inf_cd_or_prtry_cd: string
    @ivar _cdtr_ref_inf_cd_or_prtry_cd: Value of the creditor reference information from the pain message
    @type _cdtr_ref_inf_tp_issr: string
    @ivar _cdtr_ref_inf_tp_issr: Value of the creditor type Issr-field from the pain message
    @type _cdtr_ref_inf_ref: string
    @ivar _cdtr_ref_inf_ref: Value of the CrtrRef-field from the pain message
    @type _addtl_rnt_inf: Value of the AddtlRmtInf-field from the pain message
    """

    def __init__(self):
        self._rfrd_doc_inf_cd_or_prtry = None
        self._rfrd_doc_amt_cdt_note_amt = None
        self._rfrd_doc_amt_rmtd_amt = None
        self._cdtr_ref_inf_cd_or_prtry_cd = None
        self._cdtr_ref_inf_tp_issr = None
        self._cdtr_ref_inf_ref = None
        self._addtl_rnt_inf = None


class NotEnoughParametersError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)