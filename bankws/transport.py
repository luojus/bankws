'''
Overrides SUDS normal transport with version that validates certificates when
connecting to TLS protected site.

http://stackoverflow.com/questions/1087227/validate-ssl-certificates-with-python
http://stackoverflow.com/questions/6277027/suds-over-https-with-cert
http://www.threepillarglobal.com/https-client-authentication-solution-for-the-suds-soap-library
'''
import http.client
import re
import socket
import urllib.request
import urllib.error
import ssl
import sys
import os

from suds.transport.http import HttpTransport
from suds.transport.__init__ import Reply
from suds.transport.__init__ import TransportError
from logging import getLogger

log = getLogger(__name__)


class InvalidCertificateException(http.client.HTTPException,
                                  urllib.error.URLError):
    def __init__(self, host, cert, reason):
        http.client.HTTPException.__init__(self)
        self.host = host
        self.cert = cert
        self.reason = reason

    def __str__(self):
        return ('Host %s returned an invalid certificate (%s) %s\n' %
                (self.host, self.reason, self.cert))


class CertValidatingHTTPSConnection(http.client.HTTPConnection):
    default_port = http.client.HTTPS_PORT  # 443

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                             ca_certs=None, strict=None, **kwargs):
        if sys.version_info.minor < 2:
            http.client.HTTPConnection.__init__(self, host, port, strict,
                                                **kwargs)
        else:
            # Strict is depracated in newer versions.
            http.client.HTTPConnection.__init__(self, host, port, **kwargs)
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_certs = ca_certs
        if self.ca_certs:
            self.cert_reqs = ssl.CERT_REQUIRED
        else:
            self.cert_reqs = ssl.CERT_NONE

    def _GetValidHostsForCert(self, cert):
        """
        Gets common name field from certificate

        @type  cert: ssl certificate
        @param cert: Certificate that server returns when connnected.
        @rtype: string
        @return: Common name of certificate subject.
        """
        if 'subjectAltName' in cert:
            return [x[1] for x in cert['subjectAltName']
                         if x[0].lower() == 'dns']
        else:
            return [x[0][1] for x in cert['subject']
                            if x[0][0].lower() == 'commonname']

    def _ValidateCertificateHostname(self, cert, hostname):
        """

        @type  cert: ssl certificate
        @param cert: Other end ssl certificate.
        @type  hostname: string
        @param hostname: Hostname where we are connecting

        @rtype: boolean
        @return: Is the certificate issued to the host that we are connecting.
        """
        hosts = self._GetValidHostsForCert(cert)
        for host in hosts:
            host_re = host.replace('.', '\.').replace('*', '[^.]*')
            if re.search('^%s$' % (host_re,), hostname, re.I):
                return True
        return False

    def connect(self):
        """ Opens connection to other end.

        @raise L{InvalidCertificateException}: If host name and certificate
                                               host name differ.
        """
        sock = socket.create_connection((self.host, self.port))
        self.sock = ssl.wrap_socket(sock, keyfile=self.key_file,
                                          certfile=self.cert_file,
                                          cert_reqs=self.cert_reqs,
                                          ca_certs=self.ca_certs)
        if self.cert_reqs & ssl.CERT_REQUIRED:
            cert = self.sock.getpeercert()  # Get other end certificate
            hostname = self.host.split(':', 0)[0]
            if not self._ValidateCertificateHostname(cert, hostname):
                raise InvalidCertificateException(hostname, cert,
                                                  'hostname mismatch')


class VerifiedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, **kwargs):
        urllib.request.AbstractHTTPHandler.__init__(self)
        self._connection_args = kwargs

    def https_open(self, req):
        def http_class_wrapper(host, **kwargs):
            full_kwargs = dict(self._connection_args)
            full_kwargs.update(kwargs)
            return CertValidatingHTTPSConnection(host, **full_kwargs)

        try:
            return self.do_open(http_class_wrapper, req)
        except urllib.error.URLError as e:
            if type(e.reason) == ssl.SSLError and e.reason.args[0] == 1:
                raise InvalidCertificateException(req.host,
                                                  '',
                                                  e.reason.args[1])
            raise
    https_request = urllib.request.HTTPSHandler.do_request_


class HTTPSClientCertTransport(HttpTransport):
    def __init__(self, *args, **kwargs):
        HttpTransport.__init__(self, *args, **kwargs)

    def u2open(self, u2request):
        """
        Open a connection.
        @param u2request: A urllib2 request.
        @type u2request: urllib2.Requet.
        @return: The opened file-like urllib2 object.
        @rtype: fp
        """
        tm = self.options.timeout
        certpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "resources/cacerts.pem")
        handler = VerifiedHTTPSHandler(ca_certs=certpath)
        url = urllib.request.build_opener(handler)
        return url.open(u2request, timeout=tm)

    def send(self, request):
        """ Overrides Suds default send function to get 500 error messages
        parsed. """
        result = None
        url = request.url
        msg = request.message
        headers = request.headers
        try:
            u2request = urllib.request.Request(url, msg, headers)
            self.addcookies(u2request)
            self.proxy = self.options.proxy
            request.headers.update(u2request.headers)
            log.debug('sending:\n%s', request)
            fp = self.u2open(u2request)
            self.getcookies(fp, u2request)
            headers = (fp.headers.dict if sys.version_info < (3, 0)
                       else fp.headers)
            result = Reply(200, headers, fp.read())
            log.debug('received:\n%s', result)
        except urllib.error.HTTPError as e:
            if e.code in (202, 204):
                result = None
            elif e.code == 500:
                # At least Osuuspankki returns all errors on uploaded data with
                # http 500 error.
                result = Reply(500, e.fp.headers, e.fp.read())
                log.debug('received:\n%s', result)
            else:
                raise TransportError(e.msg, e.code, e.fp)
        return result
