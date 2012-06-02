"""Uploadfile module contains UploadFile-class that can be used to
generate uploadfile-messages for uploading files to bank.

Usage::
    >>> uf = UploadFile(id, environment, key, certificate)
    >>> uf.generate_message(content)
    >>> s = uf.get_request() # gets base64 encoded version of xml.

Needed external libraries:
    - LXML
"""
import base64

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
ENVIRONMENT = E.Environment
TARGET = E.TargetId
SOFTWAREID = E.SoftwareId
FILETYPE = E.FileType
CONTENT = E.Content

# Docs said that this is mandatory but examples doesn't have this value.
# and at least Osuuspankki accepts messages without UserFilename
FILENAME = E.UserFilename
# Optional fields
COMMAND = E.Command
ENCRYPTION = E.Encryption
ENCRYPTIONMETHOD = E.EncryptionMethod
COMPRESSION = E.Compression
COMPRESSIONMETHOD = E.CompressionMethod


class UploadFile(Request):
    '''
    UploadFile - class can be used to generate uploadfile messages for finnish
    banks web-services interfaces.

    @type targetid: string
    @ivar targetid: Folder where data is saved in banks side.
    @type compression: string
    @ivar compression: Is compression used in messages (defaults false as
                       software hasn't got compression support.)
    @type software: string
    @ivar software: Name of software
    @type filename: string
    @ivar filename: Name of file to be uploaded.
    @type filetype: string
    @ivar filetype: Type of file to be uploaded.
    @type key: string
    @ivar key: RSA-private key filename.
    @type certificate: string
    @ivar certificate: X509 certificate
    '''

    def __init__(self, id_, environment, key, certificate,
                 folder="target", filename="testfile.xml",
                 filetype="pain.001.001.02"):
        '''
        Initializes UploadFile class.

        @type  id_: number
        @param id_: User customerid to web services
        @type  environment: string
        @param environment: TEST or PRODUCTION
        @type  key: string
        @param key: RSA-key filename
        @type  certificate: string
        @param certificate: X509 certificate filename.
        @type  folder: string
        @param folder: Folder where data is saved on bank.
        @type  filename: string
        @param filename: Human-readable name of file.
        @type  filetype: string
        @param filetype: Type of the file being uploaded.
        '''
        Request.__init__(self, id_, environment)
        self.targetid = folder  # folder where file is saved
        self.compression = "false"
        self.software = "bankws 1.01"
        self.filename = filename
        self.filetype = filetype
        self.key = key
        self.certificate = certificate

    def generate_message(self, content):
        """
        Generates upload file message and saves it to objects text attribute.

        @type  content: string
        @param content: Data to be uploaded.
        @raise IOError: If key or certificate can't be read.
        @raise ValueError: If key is in unsupported format.
        """
        # Generate document.
        data = base64.b64encode(bytes(content, 'utf-8'))
        uploader = \
            DOC(
                CUSTOMERID(self._id),
                COMMAND("UploadFile"),  # Mandatory for NORDEA
                TIMESTAMP(timehelper.get_timestamp()),
                ENVIRONMENT(self._environment),
                FILENAME(self.filename),
                TARGET(self.targetid),
                COMPRESSION(self.compression),
                SOFTWAREID(self.software),
                FILETYPE(self.filetype),
                CONTENT(str(data, 'utf-8'))
                )
        # Sign document
        message = str(etree.tostring(uploader), 'utf-8')
        self.text = signature.sign(message, self.key, self.certificate)
