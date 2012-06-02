''' Transactionlistresponse contains classes for parsing "Tapahtumaotekysely"
events.
'''
import datetime


class BasicRecord:
    """ BasicRecord contains mainly information about customer.
    There is one BasicRecord per Tapahtumaotekysely.

    Properties::
        account - Contains customer account number
        query_date - Contains date of query
        generation_time - Contains date and time of record generation.
        account_information - Contains some extra information about account.
        bank - Contains name of the bank.
    """
    def __init__(self, message):
        """ Initializes BasicRecord

        @type  message: string
        @param message: Line from the message that contains BasicRecord.
        """
        self.material_id = message[0]  # S
        self.record_type = message[1:3]  # 00
        self.record_length = int(message[3:6])  # 322
        self.version = message[6:9]  # 001
        self._account_number = message[9:23]  # AN 14
        self.transaction_record_number = message[23:26]  # AN3 tyhja
        self._query_date_start = message[26:32]  # YYMMDD
        self._query_date_end = message[32:38]  # YYMMDD
        self._generation_time = message[38:48]  # YYMMDDHHMM
        self.customer_id = message[48:65]  # AN 17
        # not_used = message[65:71]  # N6
        # not_used = message[71:90]  # AN19
        # not_used = message[90:96]  # N6
        self._currency = message[96:99]  # AN3 currency ISO-code
        self._account_name = message[99:129]  # AN30
        self._account_limit = message[129:147]  # AN18
        self._account_owner = message[147:182]  # AN35
        self._bank = message[182:222]  # Name of the bank AN40
        # not_used = message[222:262]  # AN40
        # not_used = message[262:292]  # AN30
        # not_used = message[292:322]  # AN30

    def _get_account(self):
        """Gets account number"""
        return self._account_number.strip()

    account = property(_get_account)

    def _get_query_date(self):
        """ Gets query date

        @rtype: L{datetime.date}
        @return: Date of the query
        """
        year = int('20' + self._query_date_end[0:2])
        month = int(self._query_date_end[2:4])
        day = int(self._query_date_end[4:6])
        return datetime.date(year, month, day)

    query_date = property(_get_query_date)

    def _get_generation_time(self):
        """ Gets creation time

        @rtype: L{datetime.datetime}
        @return: Transaction record generation time
        """
        year = int('20' + self._generation_time[0:2])
        month = int(self._generation_time[2:4])
        day = int(self._generation_time[4:6])
        hour = int(self._generation_time[6:8])
        minute = int(self._generation_time[8:10])
        return datetime.datetime(year, month, day, hour, minute)

    generation_time = property(_get_generation_time)

    def _get_account_information(self):
        """ Gets extra information about account.

        @rtype: string
        @return: Extra information about account.
        """
        return ("Name: " + self._account_name.strip() + "\n" +
                "Owner: " + self._account_owner.strip() + "\n" +
                "Limit: " + self._account_limit.strip() + "\n" +
                "Currency: " + self._currency.strip())

    account_information = property(_get_account_information)

    def _get_bank(self):
        """ Gets name of the bank.

        @rtype:  string
        @return: Name of the bank.
        """
        return self._bank.strip()

    bank = property(_get_bank)


class TransactionBasicRecord():
    """ TransactionBasicRecord contain information about one
    transaction.

    Properties::
        - transaction_marker:  Name of transaction operation (debosit, intake)
        - description: Code and description for transaction.
        - money: Amount of money moved in transaction
        - name: Payee/Payer name
        - account: Payee account number
        - reference_number: Transaction reference number.
    """
    def __init__(self, message):
        """Initializes TransactionBasicRecord.

        @type  message: string
        @param message: Line from message that contains transaction.
        """
        self.material_id = message[0]  # S AN1
        self.record_type = message[1:3]  # 10  AN2
        self.record_length = message[3:6]  # N3
        self.time = message[6:12]  # N6 # HHMMSS
        self.archive_id = message[12:30]  # AN18

        # Dates
        self.registration_date = message[30:36]  # N6 # YYMMDD
        self.value_date = message[36:42]  # N6     # YYMMDD
        self.payment_date = message[42:48]  # N6   # YYMMDD

        self._transaction_marker = message[48]
        # AN1 (1, 2, 3, 4) deposit, intake, deposit fix, intake fix.

        # Kirjausselite
        self._code = message[49:52]  # AN3
        self._description = message[52:87]  # AN35
        # Amount of money in transaction
        self._sign = message[87]  # AN1
        self._amount = message[88:106]  # N18 16 kok 2 des

        self.receipt_code = message[106]  # AN1
        self.transfer_method = message[107]  # AN1

        #    Payee/Payer
        self._name = message[108:143]  # AN35
        self._name_source = message[143]  # AN1
        #    Payee account
        self._account_number = message[144:158]  # AN14
        self._account_changed = message[158]  # AN1

        self._reference_number = message[159:179]  # AN20
        #    Information about transaction
        self.form_number = message[179:187]  # AN8
        self.level_id = message[187]  # Tasotunnus # AN1 # 0

    def _get_transaction_marker(self):
        """ Gets transaction marker which tells was the transaction
        debosit or intake or fix for debosit or intake.

        @rtype: string
        @return: Textual description of transaction marker.
        """
        if self._transaction_marker == "1":
            return 'Deposit'  # pano
        elif self._transaction_marker == "2":
            return 'Intake'  # otto
        elif self._transaction_marker == "3":
            return 'Fix for deposit.'  # panon korjaus
        elif self._transaction_marker == "4":
            return 'Fix for intake.'  # oton korjaus
        else:
            return 'Unknown transaction method.'

    transaction_marker = property(_get_transaction_marker)

    def _get_description(self):
        """ Gets code and description for transaction.

        @rtype: string
        @return: Code and description in format (code: description)
        """
        return self._code + ': ' + self._description.strip()

    description = property(_get_description)

    def _get_money_in_transaction(self):
        """ Returns amount of money in transaction in such format
        that can be easily converted to Decimal datatype.

        @rtype: string
        @return: Amount of money.
        """
        amount = str(int(self._amount[:-2])) + '.' + self._amount[-2:]
        return (self._sign + amount)

    money = property(_get_money_in_transaction)

    def _get_name(self):
        """ Returns name given in transaction record.

        @rtype: string
        @return: Name if found else returns No name given.
        """
        if len(self._name.strip()) > 0:
            return self._name.strip()
        return "No name given."

    name = property(_get_name)

    def _get_account(self):
        """ Returns account number. If account number ends
        with star (*) means that account number has changed in banks
        system.

        @rtype:  string
        @return:  Account number
        """
        if self._account_changed != ' ':
            return self._account_number + '*'
        return self._account_number

    account = property(_get_account)

    def _get_reference(self):
        """ Returns reference number.

        @rtype: string
        @return: Reference number.
        """
        return self._reference_number.strip()

    reference_number = property(_get_reference)


class TransactionExtraRecord():
    """ TransactionExtraRecord contains transactions
    extra information.

    properties::
        - content: Returns tuple containing type and textual description about
        record.
    """
    def __init__(self, message):
        """ Initializes TransactionExtraRecord class.

        @type  message: string
        @param message: Line of text that contains ExtraRecord.
        """
        self.material_id = message[0]  # S AN1
        self.record_type = message[1:3]  # 11 AN2
        self.record_length = message[3:6]  # N3
        self.information_type = message[6:8]  # AN2

        if self.information_type == '00':
            # Free message (Vapaa viesti)
            message_amount = int((int(self.record_length) - 8) / 35)
            self.messages = []
            for i in range(0, message_amount):
                slice_start = i * 35 + 8
                slice_end = (i + 1) * 35 + 8
                self.messages.append(message[slice_start:slice_end])
        elif self.information_type == '01':
            # Amount of transactions
            self.transaction_amount = message[8:16]  # N8
        elif self.information_type == '02':
            # Billing info (Laskutapahtuman tiedot)
            self.customer_number = message[8:18]  # AN10
            # empty = message[18]  # AN1
            self.bill_number = message[19:34]  # AN15
            # empty = message[34]  # AN1
            self.bill_date = message[35:41]  # AN6 #YYMMDD
        elif self.information_type == '03':
            # Card payment (Korttitapahtuma)
            self.card_number = message[8:27]  # AN19
            # empty = message[27]  # AN1
            self.shop_archive_reference = message[28:42]  # AN14
        elif self.information_type == '04':
            # Fix (Korjaustapahtuma)
            self.transaction_to_be_fixed_id = message[8:26]  # AN18
        elif self.information_type == '05':
            # Currency (valuuttatapahtuma)
            # Equivalent value (Vasta-arvo)
            self.sign = message[8]  # AN1
            self.amount = message[9:27]  # N18 16 integer 2 decimal
            # empty = message[27]  # AN1
            self.currency = message[28:31]  # AN3
            # empty = message[31]  # AN1
            self.exchange_rate = message[32:43]  # N11 4 integer 7 decimal
            self.rate_reference = message[43:49]  # AN6 # Kurssiviite
        elif self.information_type == '06':
            # Applicant information (Toimeksiantajan tiedot)
            self.applicant_info_1 = message[8:43]
            self.applicant_info_2 = message[43:78]
        elif self.information_type == '07':
            # Extra information from bank
            amount = int((int(self.record_length) - 8) / 35)
            self.messages = []
            for i in range(0, amount):
                slice_start = i * 35 + 8
                slice_end = (i + 1) * 35 + 8
                self.messages.append(message[slice_start:slice_end])

        elif self.information_type == '08':
            # Payment subject (Maksun aiheen tiedot)
            self.payment_code = message[8:11]  # N3
            # tyhja = message[11]  # AN1
            self.payment_description = message[12:43]  # AN31
        elif self.information_type == '09':
            # Information about name specifier. (Nimitarkenteen tiedot)
            self.name_extension = message[8:43]  # AN35

    def _get_content(self):
        """ Gets textual description about record.

        @rtype: tuple(string, string)
        @return: infomation type, description.
        """
        content = ""
        if self.information_type == '00':
            for message in self.messages:
                content += "{0}\n".format(message.strip())
        elif self.information_type == '01':
            content = "NumberOfTransactions: {0}".format(
                                                int(self.transaction_amount)
                                                )
        elif self.information_type == '02':
            content = ("CustomerNumber: {0}\nBillNumber: {1}\nDate: {2}\n"
                       .format(self.customer_number.strip(),
                               self.bill_number.strip(),
                               self.bill_date.strip()))
        elif self.information_type == '03':
            content = "CardNumber: {0}\nShopArchive: {1}\n".format(
                                        self.card_number.strip(),
                                        self.shop_archive_reference.strip())
        elif self.information_type == '04':
            content = "ArchiveReference: {0}\n".format(
                                    self.transaction_to_be_fixed_id.strip())
        elif self.information_type == '05':
            amount = str(int(self.amount[:-2])) + "." + self.amount[-2:]
            rate = (str(int(self.exchange_rate[:4])) + "." +
                    self.exchange_rate[-7:])
            content = ("Amount: {0}{1}\nISO-Code: {2}\n"
                       "Rate: {3}\nReference: {4}\n".format(self.sign, amount,
                                                self.currency, rate,
                                                self.rate_reference.strip())
                       )
        elif self.information_type == '06':
            content = "ApplicantInfo-1: {0}\nApplicantInfo-2: {1}\n".format(
                                        self.applicant_info_1.strip(),
                                        self.applicant_info_2.strip())
        elif self.information_type == '07':
            for message in self.messages:
                content += "{0}\n".format(message.strip())
        elif self.information_type == '08':
            content = "PaymentCode: {0}\nPaymentDescription: {1}\n".format(
                                            self.payment_code.strip(),
                                            self.payment_description.strip()
                                            )
        elif self.information_type == '09':
            content = "NameExtension: {0}\n".format(
                                            self.name_extension.strip())

        return (self.information_type, content)

    content = property(_get_content)


class BalanceRecord():
    """ BalanceRecord contains info about customers
    account balance.

    properties::
        - query_date
        - balance
        - available balance
    """
    def __init__(self, message):
        """ Initializes BalanceRecord

        @type  message: string
        @param message: Line containing balance record.
        """
        self.material_id = message[0]  # AN1 S
        self.record_type = message[1:3]  # AN2 40
        self.record_length = message[3:6]  # N3 50
        self._query_date = message[6:12]  # N6 YYMMDD
        # Balance at query moment
        self._sign1 = message[12]  # AN1
        self._amount1 = message[13:31]  # N18 16 kok + 2 desima
        # Usable balance.
        self._sign2 = message[31]  # AN1
        self._amount2 = message[32:]  # AN18

    def _get_query_date(self):
        """ Returns Date of the query

        @rtype: datetime.date
        @return: Date of the query.
        """
        year = int("20" + self._query_date[:2])
        month = int(self._query_date[2:4])
        day = int(self._query_date[4:6])
        return datetime.date(year, month, day)

    query_date = property(_get_query_date)

    def _get_balance(self):
        """ Returns current balance.

        @rtype: string
        @return: Amount of money in account.
        """
        amount = str(int(self._amount1[:-2])) + "." + self._amount1[-2:]
        return (self._sign1 + amount)

    balance = property(_get_balance)

    def _get_usable_balance(self):
        """ Returns amount of usable balance

        @rtype: string
        @return: Amount of usable money.
        """
        amount = str(int(self._amount2[:-2])) + "." + self._amount2[-2:]
        return (self._sign2 + amount)

    available_balance = property(_get_usable_balance)


class InformationRecord():
    """ InformationRecord exists only if there is some error
    in query.

    Properties::
        - messages     Returns list of messages.
    """
    def __init__(self, message):
        """ Initializes InformationRecord

        @type  message: string
        @param message: Line containing information record.
        """
        self.material_id = message[0]  # AN1 S
        self.record_type = message[1:3]  # AN2 70
        self.record_length = message[3:6]  # N3
        self.bank_id = message[6:9]  # AN3
        self._messages = []
        amount_of_messages = int((int(self.record_length) - 9) / 80)
        for i in range(0, amount_of_messages):
            # Each message is 80 characters long.
            start_of_slice = 9 + i * 80
            end_of_slice = 9 + (i + 1) * 80
            self._messages.append(message[start_of_slice:end_of_slice].strip())

    def _get_messages(self):
        """ Gets messagelist

        @rtype: List<string>
        @return: List containing messages.
        """
        return self._messages

    messages = property(_get_messages)


class Transaction():
    """ Transaction structure.

    Links transaction and it's extra records
    together.

    Properties::
        transaction    Holds Transaction object
        extras         Holds list of linked extra records.
    """
    def __init__(self, transaction):
        self._transaction = transaction
        self._extras = []

    def _get_transaction(self):
        """ Gets Transaction object."""
        return self._transaction

    transaction = property(_get_transaction)

    def _get_extras(self):
        """ Gets list of extra records """
        return self._extras

    extras = property(_get_extras)

    def append_extra_record(self, record):
        """ Appends extra record to transaction

        @type  record: L{TransactionExtraRecord}
        @param record: Extra record to append.
        """
        self._extras.append(record)


class TransactionListResponse():
    """ TransactionListResponse parses Tapahtumaotekysely
    responses.

    properties::
        - basic_record     Gets BasicRecord
        - transactions     Gets list of transactions.
        - balance_record   Gets BalanceRecord
        - information_record Gets InformationRecord (if exists)
    """
    def __init__(self, message):
        records = message.splitlines()
        self._working = True
        self._transactions = []
        for record in records:
            record_id = record[1:3]
            if record_id == '00':
                # There should be only one basic record
                self._Basic = BasicRecord(record)
            elif record_id == '10':
                # There can be many transactions.
                self._transactions.append(
                    Transaction(TransactionBasicRecord(record))
                    )
            elif record_id == '11':
                # ExtraRecord is linked to transaction
                extra = TransactionExtraRecord(record)
                transaction = self._transactions.pop()
                transaction.append_extra_record(extra)
                self._transactions.append(transaction)
            elif record_id == '40':
                # There is one balance record
                self._Balance = BalanceRecord(record)
            elif record_id == '70':
                # There was some problem ...
                self._Information = InformationRecord(record)
                self._working = False

    def _get_transactions(self):
        """ Returns list of transactions """
        return self._transactions

    transactions = property(_get_transactions)

    def _get_basic_record(self):
        """ Returns BasicRecord"""
        return self._Basic

    basic_record = property(_get_basic_record)

    def _get_balance_record(self):
        """ Returns BalanceRecord"""
        return self._Balance

    balance_record = property(_get_balance_record)

    def _get_information_record(self):
        """ Returns InformationRecord """
        try:
            return self._Information
        except AttributeError:
            return None

    information_record = property(_get_information_record)

    def is_problem_free(self):
        """ Returns false if message contains InformationRecord which means
        that there was some error in processing request.

        @rtype: boolean
        @return: True if there where no errors.
        """
        return self._working
