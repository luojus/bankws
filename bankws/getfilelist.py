'''Getfilelist-module contains GetFileList-class that can be used
to generate ApplicationRequest message that is needed to list
files that bank holds.

Usage:
    >>> dfl = DownloadFileList(id_, environment, key, certificate)
    >>> dfl.generate_message(status)

External libraries:
    - Lxml
'''
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
STATUS = E.Status

# Optional fields
# Used as a filter
STARTDATE = E.StartDate
ENDDATE = E.EndDate
FILETYPE = E.FileType

COMMAND = E.Command
ENCRYPTION = E.Encryption
ENCRYPTIONMETHOD = E.EncryptionMethod


class GetFileList(Request):
    '''
    GetFileList - class can be used to generate downloadfilelist messages for
    finnish banks web-services interfaces.

    @type software: string
    @ivar software: Name of software
    @type key: string
    @ivar key: RSA-private key filename.
    @type certificate: string
    @ivar certificate: X509 certificate filename.
    @type filetype: string
    @ivar filetype: Get only files of this filetype.
    @type targetid: string
    @ivar targetid: Get files from this folder.
    '''

    def __init__(self, id_, environment, key, certificate,
                 folder=None, filetype=None):
        '''
        Initializes GetFileList class.

        @type  id_: number
        @param id_: User customerid to web services
        @type  environment: string
        @param environment: TEST or PRODUCTION
        @type  key: string
        @param key: RSA-key filename
        @type  certificate: string
        @param certificate: X509 certificate filename.
        @type  folder: string
        @param folder: Get only files from this folder.
        @type  filetype: string
        @param filetype: Get only this kind of files.
        '''
        Request.__init__(self, id_, environment)
        self.software = "bankws 1.01"
        self.key = key
        self.certificate = certificate
        # filters
        self.filetype = filetype
        self.targetid = folder  # Get only files from this folder

    def generate_message(self, status, start_date=None, end_date=None):
        """
        Generates download filelist message and saves it to objects text
        attribute.

        @type  status: string
        @param status: Status of files (NEW, DLD, ALL) (used as filter)
        @type  start_date: Date
        @param start_date: Get files starting from this date.
        @type  end_date: Date
        @param end_date: Get files ending to this date.
        @raise IOError: If key or certificate can't be read.
        @raise ValueError: If key is in unsupported format.
        """
        # Generate document.
        get_file_list = \
            DOC(
                CUSTOMERID(self._id),
                COMMAND("DownloadFileList"),  # Mandatory for NORDEA
                TIMESTAMP(timehelper.get_timestamp()),
                )

        if start_date is not None:
            get_file_list.append(STARTDATE(str(start_date)))
        if end_date is not None:
            get_file_list.append(ENDDATE(str(end_date)))

        get_file_list.append(STATUS(status))
        get_file_list.append(ENVIRONMENT(self._environment))

        if self.targetid is not None:
            get_file_list.append(TARGET(self.targetid))

        get_file_list.append(SOFTWAREID(self.software))

        if self.filetype is not None:
            get_file_list.append(FILETYPE(self.filetype))

        # Sign document
        message = str(etree.tostring(get_file_list), 'utf-8')
        self.text = signature.sign(message, self.key, self.certificate)
