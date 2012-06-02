'''Main module for webservices.

Usage::
     >>> ws = WebService(sender_id, private_key, certificate, bank)
     >>> response = ws.uploadfile(content, environment, filetype)

External libraries:
    - Suds
'''
import sys
import base64
import binascii
import logging
from datetime import date

from suds.client import Client
from suds.xsd.doctor import ImportDoctor, Import
from suds.wsse import Security, Timestamp
from suds import WebFault
from suds.transport import TransportError

try:
    from bankws import transport
    from bankws import plugin
    from bankws import idhandler
    from bankws import timehelper
    from bankws import util
    from bankws.uploadfile import UploadFile
    from bankws.getfilelist import GetFileList
    from bankws.getfile import GetFile
    from bankws.appresponse import ApplicationResponse
    from bankws.transactionlistresponse import TransactionListResponse
except ImportError:
    import transport
    import plugin
    import idhandler
    import timehelper
    import util
    from uploadfile import UploadFile
    from getfilelist import GetFileList
    from getfile import GetFile
    from appresponse import ApplicationResponse
    from transactionlistresponse import TransactionListResponse


class WebService:

    def __init__(self, sender_id, private_key, certificate, bank,
                 environment="TEST", language="FI"):
        """
        Makes soap request to bank webservice channel.

        @type  sender_id: string.
        @param sender_id: Senders id
        @type  private_key: string
        @param private_key: Private key filename.
        @type  certificate: string
        @param certificate: Filename of certificate filename.
        @type  bank: L{Bank}
        @param bank: Object containing needed data for banks web service.
        @type  environment: string
        @param environment: TEST or PRODUCTION
        @type  language: string
        @param language: Get responses in selected language (possible
                         values SV, FI and EN)
        @raise ValueError: If language is not on the list or SignerPlugin fails
                           to initialize.
        """
        self.logger = logging.getLogger("bankws")

        if not language in ["EN", "FI", "SV"]:
            error = "Unsupported language value"
            raise ValueError(error)

        env = environment.upper()
        if not env in ["TEST", "PRODUCTION"]:
            error = "Unsupported environment value."
            raise ValueError(error)

        self._environment = env
        # Fixes namespace issue from wsdl.
        schema_url = 'http://model.bxd.fi'
        schema_import = Import(schema_url)
        schema_doctor = ImportDoctor(schema_import)
        try:
            if self._environment == 'TEST':
                url = bank.wsdl_test_url
            else:
                url = bank.wsdl_url

            self._receiver_id = bank.BIC
        except AttributeError as e:
            raise ValueError("Invalid Bank object: {}".format(e))

        # Adds security header to SOAP-request.
        security = Security()
        security.tokens.append(Timestamp())
        # Generate plugin to add signature to request.
        try:
            signer = plugin.SignerPlugin(private_key, certificate)
        except (IOError, ValueError) as e:
            self.logger.error(e)
            raise ValueError("Unable to create SignerPlugin")

        self.client = Client(url, doctor=schema_doctor,
                        transport=transport.HTTPSClientCertTransport(),
                        wsse=security,
                        plugins=[signer],
                        faults=False)

        self._sender_id = sender_id
        self._language = language
        self._privatekey = private_key
        self._certificate = certificate

    def _generate_request_header(self):
        """ Generate request header for request. """
        request_id = idhandler.get_object()
        self.request_header = self.client.factory.create("ns0:RequestHeader")
        self.request_header.SenderId = self._sender_id  # ID given from bank.
        self.request_header.RequestId = request_id.next_value()  # UNIQUE ID
        self.request_header.Timestamp = timehelper.get_timestamp()
        # not required
        self.request_header.Language = self._language  # "EN" or "SV" or "FI"
        self.request_header.UserAgent = "bankws 1.01"
        self.request_header.ReceiverId = self._receiver_id  # BIC for the bank
        idhandler.save_object(request_id)

    def transaction_query(self, account_number, only_new_transactions=False):
        """ Makes transaction query.

        @type  account_number: String
        @param account_number: Account number either in BBAN or IBAN format
        @rtype: TransactionListResponse
        @return: List of days transactions
        @raise ValueError: If account number isn't valid.
        @raise RuntimeError: If request is not accepted.
        """
        branch, account = util.parse_account_number(account_number)
        # 1 All transactions for this day
        # Any other number just new transactions.
        filter_ = 0 if only_new_transactions == True else 1
        content = "$$TP1 3ST {} {} {}".format(branch, account, filter_)
        filename = "Query_{}.xml".format(date.today().isoformat())
        ret_val = self.upload_file(content, filetype_='TP1 3ST',
                                   filename_=filename)

        #Response is in content field
        #uncomment if you want to see text before parsing.
        #print(ret_val.content) 
        TLR = TransactionListResponse(ret_val.content)
        return TLR

    def upload_file(self, content, filetype_="pain.001.001.02",
                    folder_="target", filename_="test.xml"):
        """ Uploads file to bank.

        @type  content: string
        @param content: Content to be uploaded to bank.
        @type  filetype: string
        @param filetype: Type of file being uploaded.
        @type  folder: string
        @param folder: In which folder the file is saved on the bank.
        @type  filename: string
        @param filename: Userfilename for xml data.
        @rtype: L{ApplicationResponse}
        @return: Application response returned from the bank.
        @raise RuntimeError: If request was not accepted by bank.
        """
        # Generate uploadfile request.
        appdata = UploadFile(self._sender_id, self._environment,
                             self._privatekey, self._certificate,
                             folder=folder_, filename=filename_,
                             filetype=filetype_)

        try:
            appdata.generate_message(content)
        except (EnvironmentError, ValueError) as e:
            self.logger.exception(e)
            raise RuntimeError(e)

        # Uncomment if you want to see appdata before sending
        # print(appdata)
        # input("Press any key to continue...")

        self._generate_request_header()
        # Make soap request
        try:
            (status, response) = self.client.service.uploadFile(
                                            self.request_header,
                                            str(appdata.get_request(), 'utf-8')
                                            )
        except (WebFault, TransportError) as e:
            self.logger.exception(e)
            raise RuntimeError(e)
        except AttributeError as e:
            self.logger.exception(e)
            raise RuntimeError(e)
        except:
            print('Unknown exception:' + str(sys.exc_info()[0]))
            raise RuntimeError(str(sys.exc_info()[0]))

        if status != 200 and status != 500:
            raise RuntimeError("Service returned {0}".format(status))
        # Parse response
        return self._parse_response(response)

    def download_file(self, reference):
        """ Downloads file from bank.

        @type  reference: string
        @param reference: Reference id for file to be downloaded.
        @rtype: L{ApplicationResponse}
        @return: Application response returned from the bank.
        @raise RuntimeError: If request was not accepted by bank.
        """
        # Generate downloadfile request
        appdata = GetFile(self._sender_id, self._environment, self._privatekey,
                          self._certificate)
        try:
            appdata.generate_message(reference)
        except (EnvironmentError, ValueError) as e:
            self.logger.exception(e)
            raise RuntimeError(e)

        self._generate_request_header()
        # Make soap request.
        try:
            (status, response) = self.client.service.downloadFile(
                                    self.request_header,
                                    str(appdata.get_request(), 'utf-8')
                                    )
        except (WebFault, TransportError) as e:
            self.logger.exception(e)
            raise RuntimeError(e)
        except AttributeError as e:
            self.logger.exception(e)
            raise RuntimeError(e)
        except:
            print('Unknown exception:' + str(sys.exc_info()[0]))
            raise RuntimeError(str(sys.exc_info()[0]))

        if status != 200 and status != 500:
            raise RuntimeError("Service returned {0}".format(status))
        # Parse response
        return self._parse_response(response)

    def download_filelist(self, status):
        """ Downloads list of files saved to bank.

        @type  status: string
        @param status: NEW, DLD, ALL (new files, downloaded files, all)
        @rtype: L{ApplicationResponse}
        @return: Application response returned from the bank.
        @raise RuntimeError: If request is not accepted by bank.
        """
        # Generate getfilelist request.
        appdata = GetFileList(self._sender_id, self._environment,
                              self._privatekey, self._certificate)
        try:
            appdata.generate_message(status)
        except (EnvironmentError, ValueError) as e:
            self.logger.exception(e)
            raise RuntimeError(e)
        self._generate_request_header()

        # Make soap request.
        try:
            (status, response) = self.client.service.downloadFileList(
                                    self.request_header,
                                    str(appdata.get_request(), 'utf-8')
                                    )
        except WebFault as e:
            self.logger.exception(e)
            raise RuntimeError(e)
        except AttributeError as e:
            self.logger.exception(e)
            raise RuntimeError(e)
        except:
            print('Unknown exception:' + str(sys.exc_info()[0]))
            raise RuntimeError(str(sys.exc_info()[0]))

        if status != 200 and status != 500:
            raise RuntimeError("Service returned {0}".format(status))
        # Parse response
        return self._parse_response(response)

    def _parse_response(self, response):
        """
        Parses response returned from bank.

        @type  response: L{suds.sudsobject.reply}
        @param response: Response that was returned by SUDS.
        @rtype: L{ApplicationResponse}
        @return: ApplicationResponse object containing data parsed from
                 response.
        @raise RuntimeError: If request wasn't accepted.
        """
        header = response.ResponseHeader
        # Decode ApplicationResponse
        try:
            application_response = base64.b64decode(
                                       bytes(response.ApplicationResponse,
                                            'utf-8')
                                       )
            self.logger.debug(application_response)
        except binascii.Error as e:
            self.logger.exception("Failed to base64 decode response")
            raise RuntimeError(e)
        # Uncomment if you want to see message before parsing.
        # print("Message after decoding.")
        # print(application_response)
        # Check status from header.
        if header.ResponseCode != "00":
            self.logger.error("Bank didn't accept the request.")
            error_message = "{}: {}".format(header.ResponseCode,
                                            header.ResponseText)
            self.logger.error(error_message)
            if header.ResponseCode == "12":
                # Schema failure in uploaded data.
                try:
                    ar = ApplicationResponse(application_response)
                except ValueError as e:
                    # Signature wasn't valid.
                    self.logger.exception(e)

                # Error is on uploaded file.
                self.logger.error(ar.content)
                raise RuntimeError("Schema validation failed.")
            raise RuntimeError(error_message)
        # Parses application response.
        try:
            ar = ApplicationResponse(application_response)
        except ValueError as e:
            self.logger.exception(e)
            raise RuntimeError(e)

        if ar.is_accepted():
            return ar
        raise RuntimeError("Request wasn't accepted by bank.")
