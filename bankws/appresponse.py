'''
Appresponse module contains ApplicationResponse and FileDescriptor
classes which are used to parse response.

Usage:
    >>> response = ApplicationResponse(xml_message)
    >>> response.is_accepted() # Checks was the request accepted
'''
import os
import base64
import gzip
import logging

from lxml import etree

try:
    from bankws.signature import validate
except ImportError:
    from signature import validate


class ApplicationResponse():
    """ ApplicationResponse class is used to parse certificate responses

    Public methods::
        is_accepted: Checks if request was accepted (responsecode 00)
        content: Returns content of message
        references: Returns filereferences list.

    @type _customerid: string
    @ivar _customerid: Customer that send request.
    @type _timestamp: string
    @ivar _timestamp: Time and date when Application Response header was made.
    @type _responsecode: string
    @ivar _responsecode: Result of the request.
    @type _responsetext: string
    @ivar _responsetext: Human readable text telling meaning of response code.
    @type _executionserial: string
    @ivar _executionserial: Unique identifier for operation. [0..1]
    @type _encrypted: boolean
    @ivar _encrypted: Is content encrypted.
    @type _encryptionmethod: string
    @ivar _encryptionmethod: Name of the encryption algorithm.
    @type _compressed: boolean
    @ivar _compressed: Is content compressed.
    @type _compressionmethod: string
    @ivar _compressionmethod: Name of the compression algorithm.
    @type _amounttotal: string
    @ivar _amounttotal: Total sum of amounts in request.
    @type _transactioncount: string
    @ivar _transactioncount: Total number of transactions in the data.
    @type _customerextension: Element
    @ivar _customerextension: Extensions for schema.
    @type _file_descriptors: List<FileDescriptor>
    @ivar _file_descriptors: List of files founded from bank.
    @type _filetype: string
    @ivar _filetype: Type of the file.
    @type _content: string
    @ivar _content: Content of response (Usually empty, used in downloadfile
                    and schema validation error responses.)
    """
    def __init__(self, message):
        """
        Initializes ApplicationResponse class.

        @type  message: string
        @param message: ApplicationResponse xml-message.
        @raise ValueError: If message doesn't follow xml schema or
                           signature is invalid.
        """
        self.logger = logging.getLogger("bankws")

        self._accepted = True
        # validate using schema
        if not self._validate_with_schema(message):
            # Some errors return invalid xml.
            self.logger.error("Message doesn't follow schema.")
            self._accepted = False
            # raise ValueError('Failed to validate against schema')

        # Check signature
        if not validate(message):
            raise ValueError('Failed to verify signature')

        descriptors = None
        self._content = None
        tree = etree.fromstring(message)
        # Parse elements from tree to variables.
        for element in tree.iter():
            if element.tag == "{http://bxd.fi/xmldata/}CustomerId":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._customerid = element.text
            if element.tag == "{http://bxd.fi/xmldata/}Timestamp":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._timestamp = element.text
            if element.tag == "{http://bxd.fi/xmldata/}ResponseCode":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._responsecode = element.text
            if element.tag == "{http://bxd.fi/xmldata/}ResponseText":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._responsetext = element.text
            if element.tag == "{http://bxd.fi/xmldata/}ExecutionSerial":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._executionserial = element.text
            if element.tag == "{http://bxd.fi/xmldata/}Encrypted":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                value = element.text.lower()
                self._encrypted = True if value == 'true' else False
            if element.tag == "{http://bxd.fi/xmldata/}EncryptionMethod":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._encryptionmethod = element.text
            if element.tag == "{http://bxd.fi/xmldata/}Compressed":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                value = element.text.lower()
                if value == '1':
                    value = 'true'
                self._compressed = True if value == 'true' else False
            if element.tag == "{http://bxd.fi/xmldata/}CompressionMethod":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._compressionmethod = element.text
            if element.tag == "{http://bxd.fi/xmldata/}AmountTotal":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._amounttotal = element.text
            if element.tag == "{http://bxd.fi/xmldata/}TransactionCount":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._transactioncount = element.text
            if element.tag == "{http://bxd.fi/xmldata/}CustomerExtension":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._customerextension = element
            if element.tag == "{http://bxd.fi/xmldata/}FileDescriptors":
                descriptors = element
            if element.tag == "{http://bxd.fi/xmldata/}FileType":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                self._filetype = element.text
            if element.tag == "{http://bxd.fi/xmldata/}Content":
                self.logger.debug("{0}: {1}".format(element.tag, element.text))
                bytestring = bytes(element.text, 'utf-8')
                self._content = base64.b64decode(bytestring)

        # Parse filedescriptors
        if descriptors is not None:
            self._file_descriptors = []
            for descriptor in descriptors:
                fd = FileDescriptor()
                for element in descriptor.iter():
                    if element.tag == "{http://bxd.fi/xmldata/}FileReference":
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.reference = element.text
                    if element.tag == "{http://bxd.fi/xmldata/}TargetId":
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.target = element.text
                    if element.tag == "{http://bxd.fi/xmldata/}ServiceId":
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.serviceid = element.text
                    if element.tag == ("{http://bxd.fi/xmldata/}"
                                       "ServiceIdOwnerName"):
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.serviceidownername = element.text
                    if element.tag == "{http://bxd.fi/xmldata/}UserFilename":
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.userfilename = element.text
                    if element.tag == ("{http://bxd.fi/xmldata/}"
                                       "ParentFileReference"):
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.parentfile = element.text
                    if element.tag == ("{http://bxd.fi/xmldata/}FileType"):
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.filetype = element.text
                    if element.tag == "{http://bxd.fi/xmldata/}FileTimestamp":
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.timestamp = element.text
                    if element.tag == "{http://bxd.fi/xmldata/}Status":
                        self.logger.debug("{0}: {1}".format(element.tag,
                                                            element.text))
                        fd.status = element.text
                self._file_descriptors.append(fd)

    def is_accepted(self):
        """ Was applicationrequest accepted or not.

        @rtype: boolean
        @return: True if response code was 00 (OK)
        """
        try:
            if self._responsecode != "00" or self._accepted == False:
                self.logger.error(
                    "ApplicationResponse:{0}:{1}".format(self._responsecode,
                                                         self._responsetext)
                    )
                return False
            return True
        except AttributeError as e:
            self.logger.exception(e)
            self.logger.error("Unable to find responsecode and response text.")
            return False

    def _get_content(self):
        """ Returns content of xml string in clear text

        @rtype: string or None
        @return: Data saved to content field.
        """
        data = ""
        try:
            if self._compressed is True:
                if self._get_compressionmethod() != None:
                    if self._get_compressionmethod() == "RFC1952":
                        data = gzip.decompress(bytes(self._content))
                    else:
                        raise TypeError("Unsupported compression method")
                else:
                    data = gzip.decompress(bytes(self._content))
            else:
                data = self._content
            return str(data, 'utf-8')
        except AttributeError:
            return self._content

    content = property(_get_content)

    def _get_compressionmethod(self):
        """ Returns compression method used

        @rtype: string or None
        @return: Compression algorithm.
        """
        try:
            if self._compressed is True:
                return self._compressionmethod
        except AttributeError:
            return None

    def _get_filedescriptors(self):
        """ Returns list containing file descriptors.

        @rtype: list<L{FileDescriptor}>
        @return: FileDescriptors found from message.
        """
        return self._file_descriptors

    references = property(_get_filedescriptors)

    def _validate_with_schema(self, xml_string):
        """ Validates given xml string against xml schema.

        @type  xml_string: string
        @param xml_string: Xml string to be validated.
        @rtype: boolean
        @return: Is string valid against schema or not.
        """
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "resources/ApplicationResponse_20080918.xsd"
                            )
        schema_doc = etree.parse(path)
        xml_schema = etree.XMLSchema(schema_doc)
        try:
            doc = etree.fromstring(xml_string)
        except etree.XMLSyntaxError:
            self.logger.error("Invalid XML-data.")
            return False
        try:
            xml_schema.assertValid(doc)
        except etree.DocumentInvalid as e:
            self.logger.error(e)
        return xml_schema.validate(doc)


class FileDescriptor():
    """
    FileDescriptor class holds data that can be found under Filedescriptor tag.

    @type _filerefence: string
    @ivar _filerefence: Unique identifier for file (given by the bank)
    @type _target: string
    @ivar _target: Name of the folder where file is stored in bank.
    @type _serviceid: string
    @ivar _serviceid: Additional identification information of the customer.
    @type _serviceidownername: string
    @ivar _serviceidownername: Owner of the service identified by ServiceId.
    @type _userfilename: string
    @ivar _userfilename: Filename that user gave in uploadfile operation.
    @type _parentfile: string
    @ivar _parentfile: File reference to file which this file is related.
    @type _filetype: string
    @ivar _filetype: Type of the file.
    @type _timestamp: string (ISODateTime)
    @ivar _timestamp: Moment of file creation in the banks system.
    @type _status: string
    @ivar _status: State of file processing.
    """
    def __init__(self):
        """ Initializes FileDescriptor class. """
        self._reference = ""
        self._target = ""
        self._serviceid = ""
        self._serviceidownername = ""
        self._userfilename = ""
        self._parentfile = ""
        self._filetype = ""
        self._timestamp = ""
        self._status = ""

    def __str__(self):
        ret_val = "".join(["{}: {}\n".format(key[1:].title(), value)
                          for key, value in self.__dict__.items()])
        return ret_val

    def _set_reference(self, reference):
        self._reference = reference

    def _get_reference(self):
        return self._reference

    reference = property(_get_reference, _set_reference)

    def _set_target(self, target_folder):
        self._target = target_folder

    def _get_target(self):
        return self._target

    target = property(_get_target, _set_target)

    def _set_serviceid(self, serviceid):
        self._serviceid = serviceid

    def _get_serviceid(self):
        return self._serviceid

    serviceid = property(_get_serviceid, _set_serviceid)

    def _set_serviceidowner(self, name):
        self._serviceidownername = name

    def _get_serviceidowner(self):
        return self._serviceidownername

    serviceidownername = property(_get_serviceidowner, _set_serviceidowner)

    def _set_userfilename(self, filename):
        self._userfilename = filename

    def _get_userfilename(self):
        return self._userfilename

    userfilename = property(_get_userfilename, _set_userfilename)

    def _set_parent(self, parent_id):
        self._parentfile = parent_id

    def _get_parent(self):
        return self._parentfile

    parentfile = property(_get_parent, _set_parent)

    def _set_filetype(self, filetype):
        self._filetype = filetype

    def _get_filetype(self):
        return self._filetype

    filetype = property(_get_filetype, _set_filetype)

    def _set_filetimestamp(self, timestamp):
        self._timestamp = timestamp

    def _get_filetimestamp(self):
        return self._timestamp

    timestamp = property(_get_filetimestamp, _set_filetimestamp)

    def _set_status(self, status):
        self._status = status
        """codes = ["WFP", "WFC", "FWD", "DLD", "DEL", "NEW", "KIN"]
        if status in codes:
            self._status = status
        else:
            raise ValueError("Unknown code")"""

    def _get_status(self):
        return self._status

    status = property(_get_status, _set_status)
