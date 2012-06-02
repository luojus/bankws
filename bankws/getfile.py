''' Getfile - module contains GetFile class that is used to
generate ApplicationRequest message that is needed to get
file from bank.

Usage:
    >>> request = GetFile(id, environment, key, certificate)
    >>> request.generate_message(file_reference_number)

External libraries:
    - Lxml
'''
from datetime import date

from lxml.builder import ElementMaker
from lxml import etree

try:
    from bankws.request import Request
    from bankws import timehelper
    from bankws import signature
except ImportError:
    from request import Request
    import timehelper
    import signature


E = ElementMaker(namespace="http://bxd.fi/xmldata/",
                 nsmap={None: "http://bxd.fi/xmldata/"})

# Required fields for xml
DOC = E.ApplicationRequest
CUSTOMERID = E.CustomerId
TIMESTAMP = E.Timestamp
STARTDATE = E.StartDate
ENVIRONMENT = E.Environment
FILEREFERENCES = E.FileReferences
FILEREFERENCE = E.FileReference
SOFTWAREID = E.SoftwareId

# Optional fields
COMMAND = E.Command
ENCRYPTION = E.Encryption
ENCRYPTIONMETHOD = E.EncryptionMethod
COMPRESSION = E.Compression
COMPRESSIONMETHOD = E.CompressionMethod


class GetFile(Request):
    '''
    GetFile - class can be used to generate getfile messages for finnish
    banks web-services interfaces.

    @type compression: string
    @ivar compression: Is compression used in messages. (Default false)
    @type software: string
    @ivar software: Name of software
    @type key: string
    @ivar key: RSA-private key filename.
    @type certificate: string
    @ivar certificate: X509 certificate filename.
    '''

    def __init__(self, id_, environment, key, certificate,
                 compression=False):
        '''
        Initializes GetFile class.

        @type  id_: number
        @param id_: User customerid to web services
        @type  environment: string
        @param environment: TEST or PRODUCTION
        @type  key: string
        @param key: RSA-key filename.
        @type  certificate: string
        @param certificate: X509 certificate filename.
        @type  compression: boolean
        @param compression: Is returned file compressed.
        '''
        Request.__init__(self, id_, environment)
        self.compression = "true" if compression is True else "false"
        self.software = "bankws 1.01"
        self.key = key
        self.certificate = certificate

    def generate_message(self, reference, start_date=None):
        """
        Generates downloadfile message and saves it to objects text attribute.

        @type  reference: string
        @param reference: Reference number of file wanted.
        @type  start_date: L{date}
        @param start_date: Filters out older files (?)
        @raise IOError: If key or certificate can't be read.
        @raise ValueError: If key is in unsupported format.
        """
        # Generate document.
        # Startdate should be optional but OP example used it.
        if start_date is None:
            startdate = str(date.today())
        else:
            startdate = str(start_date)

        get_file = \
            DOC(
                CUSTOMERID(self._id),
                COMMAND("DownloadFile"),  # Mandatory for NORDEA
                TIMESTAMP(timehelper.get_timestamp()),
                STARTDATE(startdate),
                ENVIRONMENT(self._environment),
                FILEREFERENCES(
                    FILEREFERENCE(reference)
                ),
                COMPRESSION(self.compression),
                SOFTWAREID(self.software),
                )
        # Sign document
        message = str(etree.tostring(get_file), 'utf-8')
        self.text = signature.sign(message, self.key, self.certificate)
