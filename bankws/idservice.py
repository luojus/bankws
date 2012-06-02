"""
Signs certificate request using Osuuspankki Tunnistepalvelu

Needed libraries:
    Suds - handles soap requests and responses
    Lxml - Xml handling
    PyOpenSSL - signature handling
    PyCrypto - RSA related stuff

Generate rsa keys:
    >>>openssl req -newkey rsa:2048 -keyout key.pem -out req.der -outform DER
When openssl asks for country enter: FI
When openssl asks for common name: enter your customerid
Remove pass phrase from private key:
    >>> cp key.pem  key.pem.org
    >>> openssl rsa -in key.pem.org -out key.pem
"""
import sys
import logging
import base64
import binascii

from suds import client
from suds import WebFault
from suds.plugin import MessagePlugin

try:
    from bankws import carequest as CAR
    from bankws import caresponse
    from bankws import idhandler
    from bankws import timehelper
    from bankws import transport
except ImportError:
    import carequest as CAR
    import caresponse
    import idhandler
    import timehelper
    import transport


class OPCertificateRequest():

    def __init__(self, sender_id, mode='TEST'):
        """
        @type  sender_id: integer
        @param sender_id: ID given by Osuuspankki.
        @type  certificate_request: string
        @param certificate_request: Name of Certificate request file.
        @type  mode: string
        @param mode: TEST or PRODUCTION
        @raises ValueError: If mode is not TEST or PRODUCTION
        """
        self.log = logging.getLogger('bankws')

        env = mode.upper()
        if not env in ["TEST", "PRODUCTION"]:
            error = "Unsupported environment value."
            raise ValueError(error)

        if env == 'TEST':
            url = 'https://wsk.asiakastesti.op.fi/wsdl/MaksuliikeCertService.xml'
        else:
            url = 'https://wsk.op.fi/wsdl/MaksuliikeCertService.xml'

        # Create new soap client using validating secure transport layer
        self.client = client.Client(url,
                          plugins=[MyPlugin()],
                          transport=transport.HTTPSClientCertTransport(),
                          faults=False)

        self.sender_id = sender_id
        self.environment = mode

    def generate_header(self):
        request_id = idhandler.get_object()  # Gets idhandler object

        # Generate header for the certificate request
        self.request_header = self.client.factory.create(
                                    'CertificateRequestHeader'
                                    )
        self.request_header.SenderId = self.sender_id            # SENDER ID
        self.request_header.RequestId = request_id.next_value()  # UNIQUE ID
        self.request_header.Timestamp = timehelper.get_timestamp()

        # Save request_id back to file
        idhandler.save_object(request_id)

    def request_with_transferkey(self, transferkey_, certificate_request,
                                 certificate):
        """ Requests certificate signing with transferkey.

        @type  certificate_request: string
        @param certificate_request: Name of Certificate request file.
        @type  transferkey_: integer
        @param transferkey_: Transferkey needed to get first certificate.
        @type  certificate: string
        @param certificate: Filename where certificate is saved.
        @rtype:  boolean
        @return: Is request accepted or not.
        """
        try:
            self.log.info('Generating request object.')
            request = CAR.CertificateRequest(self.sender_id, self.environment,
                                             transferkey=transferkey_)
        except RuntimeError as e:
            self.log.exception(e)
            return False

        # Generate request
        if not request.request_with_transferkey(certificate_request):
                self.log.error('Unable to open certificate request.')
                return False

        message = request.get_request()  # Gets message from object.
        self.generate_header()
        # Send soap certificate request to bank
        try:
            self.log.info("Sending request to bank.")
            (status, response) = self.client.service.getCertificate(
                                                self.request_header,
                                                message.decode('utf-8')
                                                )
        except WebFault as e:
            self.log.exception(e)
            return False
        except AttributeError as e:
            self.logger.exception(e)
            return False
        except:
            print('Unknown exception:' + str(sys.exc_info()[0]))
            return False

        if status != 200 and status != 500:
            print("Service returned {0}".format(status))
            return False

        self.log.debug(response)
        header = response.ResponseHeader
        application_response = response.ApplicationResponse
        # Check response and try to parse message.

        if header.ResponseCode == "00":
            try:
                # Decode ApplicationResponse
                message = base64.b64decode(
                                    bytes(application_response, 'utf-8')
                                    )
            except binascii.Error as e:
                self.log.exception(e)
                return False

            # Parse response and save certificate back to file
            try:
                caresponse.CertificateResponse(message, certificate)
            except (ValueError, RuntimeError) as e:
                self.log.exception(e)
                return False
        else:
            self.log.error("ResponseCode {0}:{1}".format(header.ResponseCode,
                                                         header.ResponseText))
            return False

        return True

    def request_with_old_certificate(self, privatekey, certificate_request,
                                     certificate,
                                     certificate_filename=None):
        """ Request certificate with existing certificate

        @type  certificate_request: string
        @param certificate_request: Name of Certificate request file.
        @type  privatekey: integer
        @param privatekey: Privatekey linked to old certificate.
        @type  certificate: string
        @param certificate: Filename of old certificate.
        @type  certificate_filename: string
        @param certificate_filename: Filename where new certificate is saved
                                     (if None saves over old certificate)
        @rtype:  boolean
        @return: Is request accepted or not.
        """
        try:
            self.log.info('Generating request object.')
            request = CAR.CertificateRequest(self.sender_id, self.environment)
        except RuntimeError as e:
            self.log.exception(e)
            return False
        if not request.request_with_old_certificate(certificate_request,
                                                    privatekey,
                                                    certificate):
            self.log.error("Unable to open certificate request.")
            return False

        message = request.get_request()  # Gets message from object.
        self.generate_header()

        # Send soap certificate request to bank
        try:
            self.log.info("Sending request to bank.")
            (status, response) = self.client.service.getCertificate(
                                                self.request_header,
                                                message.decode('utf-8')
                                                )
        except WebFault as e:
            self.log.exception(e)
            return False
        except AttributeError as e:
            self.logger.exception(e)
            return False
        except:
            print('Unknown exception:' + str(sys.exc_info()[0]))
            return False

        if status != 200 and status != 500:
            print("Service returned {0}".format(status))
            return False

        self.log.debug(response)
        header = response.ResponseHeader
        application_response = response.ApplicationResponse
        # Check response and try to parse message.

        if header.ResponseCode == "00":
            try:
                # Decode ApplicationResponse
                message = base64.b64decode(
                                    bytes(application_response, 'utf-8')
                                    )
            except binascii.Error as e:
                self.log.exception(e)
                return False

            # Parse response and save certificate back to file
            try:
                if certificate_filename is None:
                    caresponse.CertificateResponse(message, certificate)
                else:
                    caresponse.CertificateResponse(message,
                                                   certificate_filename,
                                                   certificate)
            except (ValueError, RuntimeError) as e:
                self.log.exception(e)
                return False
        else:
            self.log.error("ResponseCode {0}:{1}".format(header.ResponseCode,
                                                         header.ResponseText))
            return False

        return True

    def get_certificates(self):
        """ Lists certificates saved on this customer id

        @rtype: tuple(boolean, CertificateResponse)
        @return: Returns CertificateResponse if request was accepted else None.
        """
        try:
            self.log.info('Generating request object.')
            request = CAR.CertificateRequest(self.sender_id, self.environment)
        except RuntimeError as e:
            self.log.exception(e)
            return (False, None)

        # Generate request
        request.get_certificates()

        message = request.get_request()  # Gets message from object.
        self.generate_header()
        # Send soap certificate request to bank
        try:
            self.log.info("Sending request to bank.")
            (status, response) = self.client.service.getServiceCertificates(
                                                self.request_header,
                                                message.decode('utf-8')
                                                )
        except WebFault as e:
            self.log.exception(e)
            return (False, None)
        except AttributeError as e:
            self.logger.exception(e)
            return (False, None)
        except:
            print('Unknown exception:' + str(sys.exc_info()[0]))
            return (False, None)

        if status != 200 and status != 500:
            print("Service returned {0}".format(status))
            return (False, None)

        self.log.debug(response)
        header = response.ResponseHeader
        application_response = response.ApplicationResponse
        # Check response and try to parse message.

        if header.ResponseCode == "00":
            try:
                # Decode ApplicationResponse
                message = base64.b64decode(
                                    bytes(application_response, 'utf-8')
                                    )
            except binascii.Error as e:
                self.log.exception(e)
                return (False, None)

            # Parse response and save certificate back to file
            try:
                cert_response = caresponse.CertificateResponse(message,
                                                            list_only=True)
            except (ValueError, RuntimeError) as e:
                self.log.exception(e)
                return (False, None)
            else:
                return (True, cert_response)
        else:
            self.log.error("ResponseCode {0}:{1}".format(header.ResponseCode,
                                                         header.ResponseText))
            return (False, None)


class MyPlugin(MessagePlugin):
    """ Prints messages that are received and sent, if logger has debug
    level on. """
    def marshalled(self, context):
        self.log = logging.getLogger("bankws")
        # Prints xml message to be sent.
        body = context.envelope.getRoot()
        self.log.debug(body)

    def received(self, context):
        self.log.debug(context.reply)
