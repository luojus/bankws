'''Carequest module contain CertApplicationRequest class that can be
used to generate certificate requests for Osuuspankki Web Services.

Usage::
    >>> request = CertificateRequest(id, environment, transferkey)
or
    >>> request = CertificateRequest(id, environment)
Generate actual request:
    >>> request.request_with_transferkey(certificate_request)
or
    >>> request.request_with_old_certificate(certificate_request, private_key,
                                             certificate)

External libraries:
    - Lxml
'''
import base64
import logging

from lxml.builder import ElementMaker
from lxml import etree

try:
    from bankws.request import Request
    from bankws.util import check_luhn_modulo10
    from bankws import signature
    from bankws import timehelper
except ImportError:
    from request import Request
    from util import check_luhn_modulo10
    import signature
    import timehelper

E = ElementMaker(namespace="http://op.fi/mlp/xmldata/",
                 nsmap={None: "http://op.fi/mlp/xmldata/"})

DOC = E.CertApplicationRequest
CUSTOMERID = E.CustomerId
TIMESTAMP = E.Timestamp
ENVIRONMENT = E.Environment
SOFTWAREID = E.SoftwareId
COMMAND = E.Command
EXECUTIONSERIAL = E.ExecutionSerial
ENCRYPTION = E.Encryption
ENCRYPTIONMETHOD = E.EncryptionMethod
COMPRESSION = E.Compression
COMPRESSIONMETHOD = E.CompressionMethod
SERVICE = E.Service
CONTENT = E.Content
TRANSFERKEY = E.TransferKey
SERIALNUMBER = E.SerialNumber


class CertificateRequest(Request):
    def __init__(self, id_, environment, transferkey=None, serial_number=None):
        """ Constructor for CertificateRequest class.

        @type  transferkey: int
        @param transferkey: Osuuspankki Transferkey
        @type  serial_number: int
        @param serial_number: Certificate serial number
        @raise RuntimeError: If transferkey is invalid.
        """
        Request.__init__(self, id_, environment)
        self.logger = logging.getLogger("bankws")

        if transferkey:
            if check_luhn_modulo10(str(transferkey)):
                self.logger.info("Transferkey accepted.")
                self._transferkey = str(transferkey)
            else:
                self.logger.error("Transferkey rejected.")
                raise RuntimeError("Not valid transferkey")
        if serial_number:
            self._serial_number = str(serial_number)
        self._command = None
        self._content = None
        self._service = "MATU"
        self._software = "BANKWS 1.01"

    def request_with_transferkey(self, certificate_request):
        """ Generates CertApplicationMessage that uses transferkey
        as identifier.

        @type  sertificate: string
        @param sertificate: Certificate request filename.
        @rtype: boolean
        @return: True if certificate request exists.
        """
        try:
            with open(certificate_request, 'rb') as f:
                content = f.read()
        except EnvironmentError as e:
            self.logger.exception(e)
            return False

        certreq = DOC(
                    CUSTOMERID(self._id),
                    TIMESTAMP(timehelper.get_timestamp()),
                    ENVIRONMENT(self._environment),
                    SOFTWAREID(self._software),
                    COMPRESSION("false"),
                    SERVICE(self._service),
                    CONTENT(str(base64.b64encode(content), "utf-8")),
                    TRANSFERKEY(self._transferkey)
                    )

        self.logger.debug(etree.tostring(certreq, xml_declaration=True,
                                         encoding="UTF-8",
                                         pretty_print=True).decode('utf8')
                         )

        self.text = etree.tostring(certreq,
                                   xml_declaration=True,
                                   encoding="UTF-8")
        return True

    def request_with_serial(self):
        """ Generates certificate request using serial number."""
        try:
            serial = self._serial_number
        except AttributeError as e:
            self.logger.exception(e)
            raise RuntimeError(
                    "You need to give serial number in class constructor"
                    )

        certreq = DOC(
                    CUSTOMERID(self._id),
                    TIMESTAMP(timehelper.get_timestamp()),
                    ENVIRONMENT(self._environment),
                    SOFTWAREID(self._software),
                    COMPRESSION("false"),
                    SERVICE(self._service),
                    SERIALNUMBER(serial)
                    )
        self.logger.debug(etree.tostring(certreq, xml_declaration=True,
                                         encoding="UTF-8",
                                         pretty_print=True).decode('utf8')
                         )
        self.text = etree.tostring(certreq,
                                   xml_declaration=True,
                                   encoding="UTF-8")

    def request_with_old_certificate(self, certificate_request, private_key,
                                     certificate):
        """
        Generates request needed for getting new certificate with existing
        certificate.

        @type  certificate_request: string
        @param certificate_request: Filename of certificate request.
        @type  private_key: string
        @param private_key: Filename of RSA-private key.
        @type  certificate: string
        @param certificate: Filename of old certificate
        """
        # Read certificate request.
        try:
            with open(certificate_request, 'rb') as f:
                content = f.read()
        except EnvironmentError as e:
            self.logger.exception(e)
            return False
        # Generate xml string
        certreq = DOC(
                    CUSTOMERID(self._id),
                    TIMESTAMP(timehelper.get_timestamp()),
                    ENVIRONMENT(self._environment),
                    SOFTWAREID(self._software),
                    COMPRESSION("false"),
                    SERVICE(self._service),
                    CONTENT(str(base64.b64encode(content), "utf-8"))
                    )

        self.logger.debug(etree.tostring(certreq, xml_declaration=True,
                                         encoding="UTF-8",
                                         pretty_print=True).decode('utf8')
                         )
        xml_string = str(etree.tostring(certreq), "utf-8")
        # Sign xml string with old key and certificate.
        try:
            self.text = signature.sign(xml_string,
                                       private_key,
                                       certificate,
                                       xml_declaration_=True)
        except (EnvironmentError, ValueError) as e:
            self.logger.exception(e)
            return False
        return True

    def get_certificates(self):
        """ Gets all certificates saved to customerid """
        certreq = DOC(
                    CUSTOMERID(self._id),
                    TIMESTAMP(timehelper.get_timestamp()),
                    ENVIRONMENT(self._environment),
                    SOFTWAREID(self._software),
                    SERVICE(self._service)
                    )

        self.logger.debug(etree.tostring(certreq, xml_declaration=True,
                                         encoding="UTF-8",
                                         pretty_print=True).decode('utf8')
                         )
        self.text = etree.tostring(certreq,
                                   xml_declaration=True,
                                   encoding="UTF-8")
