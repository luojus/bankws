"""
CertificateResponse module contains CertificateResponse class that can be used
to parse CertificateResponses coming from Osuuspankki Tunnistepalvelu.

External libraries:
    LXML - Xml handling
External resources:
    CertApplicationResponse_200812.xsd - CertificateResponse XML Schema

Parse response:
>>> try:
        response = CertificateResponse(responsemessage, filename)
    except ValueError as e:
        print(e)
    except RuntimeError as e:
        print(e)
"""
import base64
import os
import logging
import errno

from lxml import etree

try:
    from bankws.signature import validate
except ImportError:
    from signature import validate


class CertificateResponse():
    """ CertificateResponse class is used to parse certificate responses

    @type logger: logging.Logger
    @ivar logger: General logger for bankws.
    @type _customerid: string
    @ivar _customerid: CustomerId that bank gave.
    @type _timestamp: string
    @ivar _timestamp: Message generation time.
    @type _responsecode: string
    @ivar _responsecode: Responsecode for request.
    @type _responsetext: string
    @ivar _responsetext: Human-readable form of responsecode.
    @type _certificates: lxml._element
    @ivar _certificates: Xml-element that contains certificates.
    @type _common_name: string
    @ivar _common_name: CommonName field in certificate
    @type _country: string
    @ivar _country: Country field in certificate.
    @type _certificate_format: string
    @ivar _certificate_format: Format of returned certificate.
    """
    def __init__(self, message, filename='op.crt', old_filename=None,
                 list_only=False):
        """
        Initializes CertificateResponse class.

        @type  message: string
        @param message: CertApplicationResponse xml message.
        @type  filename: string
        @param filename: Filename where certificate is saved.
        @type  old_filename: string
        @param old_filename: Certificate old filename. (used for dublicate
                             detection)
        @type  list_only: boolean
        @param list_only: Only lists certificates (doesn't save them on file)
        @raise ValueError: If message doesn't follow xml schema or
                           signature is invalid.
        @raise RuntimeError: If message response code is different than OO
        """
        self.logger = logging.getLogger("banksws")
        # validate using schema
        if not self._validate_with_schema(message):
            self.logger.error("Invalid xml")
            raise ValueError('Failed to validate against schema')
        # Check signature
        if not validate(message):
            self.logger.error("Invalid signature")
            raise ValueError('Failed to verify signature')

        tree = etree.fromstring(message)
        for element in tree.iter():
            if element.tag == "{http://op.fi/mlp/xmldata/}CustomerId":
                self._customerid = element.text
            if element.tag == "{http://op.fi/mlp/xmldata/}Timestamp":
                self._timestamp = element.text
            if element.tag == "{http://op.fi/mlp/xmldata/}ResponseCode":
                self._responsecode = element.text
            if element.tag == "{http://op.fi/mlp/xmldata/}ResponseText":
                self._responsetext = element.text
            if element.tag == "{http://op.fi/mlp/xmldata/}Certificates":
                self._certificates = element

        if self._responsecode != "00":
            error = "Error " + self._responsecode + ": " + self._responsetext
            self.logger.info("Request was not accepted.")
            raise RuntimeError(error)

        self.certificates = []

        for element in self._certificates.findall(
                            "{http://op.fi/mlp/xmldata/}Certificate"
                            ):
            cert = Certificate()
            for el in element.iterchildren():
                if el.tag == "{http://op.fi/mlp/xmldata/}Name":
                    self.logger.info(el.text)
                    cert.name = el.text
                    # common_name, country = el.text.split(',')
                    # self._common_name = common_name.split('=')[1]
                    # self._country = country.split('=')[1]
                if el.tag == "{http://op.fi/mlp/xmldata/}Certificate":
                    cert.certificate = base64.b64decode(
                                                bytes(el.text, 'utf-8')
                                                )
                if el.tag == "{http://op.fi/mlp/xmldata/}CertificateFormat":
                    self.logger.info(el.text)
                    cert.certificate_format = el.text
            self.certificates.append(cert)

        if len(self.certificates) > 1 or list_only == True:
            for cert in self.certificates:
                print("Common name:{0}".format(cert.name))
                print("Certicate (Base64 encoded): {0}".format(
                                        base64.b64encode(cert.certificate))
                                        )
                print("Certificate Format: {0}".format(
                                        cert.certificate_format)
                                        )
            return

        if old_filename is None:
            old_filename = filename

        if os.path.isfile(old_filename):
            with open(old_filename, 'rb') as f:
                old_certificate = f.read()
            if len(self.certificates) > 0:
                cert = self.certificates[0].certificate
                if cert is not None:
                    if old_certificate == cert:
                        self.logger.error("Duplicate certificate.")
                        raise RuntimeError('Same certificate as before.')
                else:
                    raise RuntimeError("Certificate not found.")
            else:
                raise RuntimeError("Certificate not found.")

        self.save_certificate_to_file(filename)

    def _validate_with_schema(self, xml_string):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "resources/CertApplicationResponse_200812.xsd"
                            )
        xml_schema_doc = etree.parse(path)
        xml_schema = etree.XMLSchema(xml_schema_doc)
        try:
            doc = etree.fromstring(xml_string)
        except etree.XMLSyntaxError:
            return False

        return xml_schema.validate(doc)

    def save_certificate_to_file(self, filename):
        self.logger.info("Saving certificate to {0}".format(filename))
        # First try to save directly.
        try:
            with open(filename, 'wb') as certificate_file:
                certificate_file.write(self.certificates[0].certificate)
        except IOError as e:
            if e.errno != errno.ENOENT:  # No such file or directory
                print(e)
                print("Certificate (base64 encoded): {0}".format(
                    base64.b64encode(self.certificates[0].certificate)
                    )
                )
                return
            # Lets check if error was caused by missing directory
            dir_ = os.path.dirname(filename)
            # Check does the folder exists
            if not os.path.exists(dir_):
                # Check that path doesn't contain os.pardir (..) characters
                if os.pardir in dir_:
                    print("makedirs() will become confused if the path"
                          " elements to create include pardir.")
                    print("Certificate (base64 encoded): {0}".format(
                            base64.b64encode(self.certificates[0].certificate)
                            )
                      )
                    return
                # Try to create missing directories
                try:
                    os.makedirs(dir_)
                except OSError as e:
                    print(e)
                    print("Certificate (base64 encoded): {0}".format(
                            base64.b64encode(self.certificates[0].certificate)
                            )
                      )
                    return

                if not os.path.exists(dir_):
                    print("Unable to generate requested directory")
                    print("Certificate (base64 encoded): {0}".format(
                            base64.b64encode(self.certificates[0].certificate)
                            )
                      )
                    return
                try:
                    with open(filename, 'wb') as certificate_file:
                        certificate_file.write(self.certificates[0].certificate)
                except EnvironmentError as e:
                    print(e)
                    print("Unable to save certificate to {}".format(filename))
                    print("Certificate (base64 encoded): {0}".format(
                            base64.b64encode(self.certificates[0].certificate)
                            )
                    )
                    return
            else:
                # Just to be sure that user is informed in every scenario.
                print("Unable to save certificate to {}".format(filename))
                print("Certificate (base64 encoded): {0}".format(
                            base64.b64encode(self.certificates[0].certificate)
                            )
                    )


class Certificate():
    """ Structure to save certificate info """
    def __init__(self):
        self._name = None
        self._certificate = None
        self._format = None

    def _get_name(self):
        return self._name

    def _set_name(self, name):
        self._name = name

    name = property(_get_name, _set_name)

    def _get_certificate(self):
        return self._certificate

    def _set_certificate(self, certificate):
        self._certificate = certificate

    certificate = property(_get_certificate, _set_certificate)

    def _get_format(self):
        return self._format

    def _set_format(self, format_):
        self._format = format_

    certificate_format = property(_get_format, _set_format)
