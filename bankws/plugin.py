'''Plugin module contains SignerPlugin-class that is used as suds
messageplugin. Plugin adds wsse-signature to outgoing message and
validates incoming messages.

Modified version of https://github.com/dnet/SudsSigner/blob/master/plugin.py

Needed external libraries:
    - Lxml
    - Suds
'''
import base64
import logging
import os
from uuid import uuid4

from lxml import etree
from suds.plugin import MessagePlugin
from suds.bindings.binding import envns
from suds.wsse import wsuns, dsns, wssens
import Crypto.PublicKey.RSA as RSAKey

try:
    from bankws import signature
except ImportError:
    import signature


def lxml_ns(suds_ns):
    """Converts suds namespace declaration to lxml namespace declaration"""
    return dict((suds_ns,))


def ns_id(tagname, suds_ns):
    """Adds namespace to tag"""
    return '{{{0}}}{1}'.format(suds_ns[1], tagname)

# Namespace declarations.
NSMAP = dict((dsns, wssens, wsuns))
LXML_ENV = lxml_ns(envns)
# Precompiled XPath expressions.
BODY_XPATH = etree.XPath('/SOAP-ENV:Envelope/SOAP-ENV:Body',
                         namespaces=LXML_ENV)
HEADER_XPATH = etree.XPath('/SOAP-ENV:Envelope/SOAP-ENV:Header',
                           namespaces=LXML_ENV)
SECURITY_XPATH = etree.XPath('wsse:Security',
                             namespaces=lxml_ns(wssens))
TIMESTAMP_XPATH = etree.XPath('wsu:Timestamp',
                              namespaces=lxml_ns(wsuns))
# Identifiers for used methods.
C14N = 'http://www.w3.org/2001/10/xml-exc-c14n#'
XMLDSIG_SHA1 = 'http://www.w3.org/2000/09/xmldsig#sha1'
DSA = 'http://www.w3.org/2000/09/xmldsig#dsa-sha1'
RSA = 'http://www.w3.org/2000/09/xmldsig#rsa-sha1'

X509 = ("http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token"
        "-profile-1.0#X509v3")
X509BASE64 = ("http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap"
              "-message-security-1.0#Base64Binary")


class SignerPlugin(MessagePlugin):
    """
    SignerPlugin class adds wsse signature to outgoing soap request and
    verifies that incoming message signature is valid.

    @type keyfile: string
    @ivar keyfile: Private RSA-key filename
    @type certificate: string
    @ivar certificate: X509v3 DER certificate filename.
    @type keytype: string
    @ivar keytype: Identifier for rsa-sha1
    """
    def __init__(self, private_key, certificate):
        """
        Initializes Suds MessagePlugin.

        @type  private_key: string
        @param private_key: RSA - private key filename.
        @type  certificate: string
        @param certificate: X509 certificate filename.
        """
        self.log = logging.getLogger('bankws')
        if os.path.isfile(private_key):
            with open(private_key, 'rb') as f:
                content = f.read()
            try:
                RSAKey.importKey(content)
            except ValueError:
                raise ValueError('Unsupported RSA key format')
            self.keyfile = private_key
        else:
            raise IOError("{0} doesn't exists".format(private_key))

        if os.path.isfile(certificate):
            self.certificate = certificate
        else:
            raise IOError("{0} doesn't exists".format(certificate))
        self.keytype = RSA

    def received(self, context):
        """ Checks signature validity"""
        self.log.info("Received data: {0}".format(context.reply))
        env = etree.fromstring(context.reply)
        valid = signature.validate(etree.tostring(env))
        if not valid:
            raise RuntimeError("Invalid signature")

    def sending(self, context):
        """ Adds wsse-signature to Soap-envelope.

        @type  context: Bytes
        @param context: Suds generated Soap-envelope.
        """
        env = etree.fromstring(context.envelope)
        (body,) = BODY_XPATH(env)
        queue = SignQueue()
        queue.push_and_mark(body)
        security = ensure_security_header(env, queue)
        security_id = self.insert_binary_security_token(security, queue)
        self.insert_signature_template(security, security_id, queue)
        context.envelope = self.get_signature(etree.tostring(env))
        self.log.info("Signed envelope: {0}".format(context.envelope))

    def insert_signature_template(self, security, security_id, queue):
        """
        Inserts base for xml signature.

        @type  security: L{lxml.etree._Element}
        @param security: WSSE security header.
        @type  security_id: string
        @param security_id: BinarySecurityTokens id
        @type  queue: L{SignQueue}
        @param queue: Queue containing used Id's.
        """
        signature = etree.SubElement(security, ns_id('Signature', dsns))
        self.append_signed_info(signature, queue)
        etree.SubElement(signature, ns_id('SignatureValue', dsns))
        self.append_key_info(signature, security_id)

    def insert_binary_security_token(self, security, queue):
        """
        Inserts certificate data in BinarySecurityToken element.

        @type  security: L{lxml.etree._Element}
        @param security: WSSE security header.
        @type  queue: L{SignQueue}
        @param queue: Queue for id generation.
        @rtype: string
        @return: BinarySecurityToken ID
        @raise IOError: If certificate file is not found.
        """
        binsec = etree.SubElement(security,
                                  ns_id('BinarySecurityToken', wssens),
                                  ValueType=X509,
                                  EncodingType=X509BASE64
                                  )
        id_ = queue.mark(binsec)
        with open(self.certificate, "rb") as f:
            content = f.read()
            binsec.text = base64.b64encode(content)
        return id_

    def append_signed_info(self, signature, queue):
        """
        Appends signed info element to signature.

        @type  signature: L{lxml.etree._Element}
        @param signature: Signature element.
        @type  queue: L{SignQueue}
        @param queue: Queue containing used Id's.
        """
        signed_info = etree.SubElement(signature, ns_id('SignedInfo', dsns))
        set_algorithm(signed_info, 'CanonicalizationMethod', C14N)
        set_algorithm(signed_info, 'SignatureMethod', self.keytype)
        queue.insert_references(signed_info)

    def append_key_info(self, signature, security_id):
        """
        Insert key info element.

        @type  signature: L{lxml.etree._Element}
        @param signature: ...
        @type  security_id: string
        @param security_id: BinarySecurityToken id.
        """
        key_info = etree.SubElement(signature, ns_id('KeyInfo', dsns))
        sec_token_ref = etree.SubElement(key_info,
                                    ns_id('SecurityTokenReference', wssens))
        etree.SubElement(sec_token_ref, ns_id('Reference', wssens),
                         URI="#" + security_id,
                         ValueType=X509)

    def get_signature(self, envelope):
        """
        Signs given xml envelope.

        @type  envelope: bytes
        @param envelope: Xml string to sign.
        @rtype: string
        @return: Signed xml string.
        """
        # Serialize xml string.
        doc = etree.fromstring(envelope)
        # Find soap body element and calculate digest for it.
        body = BODY_XPATH(doc)[0]
        body_id = body.attrib['{' + wsuns[1] + '}Id']
        digest = signature.calculate_digest(str(etree.tostring(body), 'utf-8'),
                                            exclusive_=True)

        body_digest = base64.b64encode(digest.digest())

        # Find timestamp element and calculate digest for it.
        header = HEADER_XPATH(doc)[0]
        security = SECURITY_XPATH(header)[0]
        timestamp = TIMESTAMP_XPATH(security)[0]
        timestamp_id = timestamp.attrib['{' + wsuns[1] + '}Id']
        CREATED_XPATH = etree.XPath('wsu:Created',
                                    namespaces=lxml_ns(wsuns))

        EXPIRED_XPATH = etree.XPath('wsu:Expires',
                                    namespaces=lxml_ns(wsuns))
        created = CREATED_XPATH(timestamp)[0]
        expired = EXPIRED_XPATH(timestamp)[0]
        created.text = created.text.split(".")[0] + 'Z'
        expired.text = expired.text.split(".")[0] + 'Z'
        digest = signature.calculate_digest(
                                str(etree.tostring(timestamp), 'utf-8'),
                                exclusive_=True)

        timestamp_digest = base64.b64encode(digest.digest())

        # Search all reference elements.
        SIGNATURE_XPATH = etree.XPath('ds:Signature',
                                      namespaces=lxml_ns(dsns))
        signature_ = SIGNATURE_XPATH(security)[0]
        SIGNEDINFO_XPATH = etree.XPath('ds:SignedInfo',
                                       namespaces=lxml_ns(dsns))
        signed_info = SIGNEDINFO_XPATH(signature_)[0]

        references = signed_info.findall(
                        '{http://www.w3.org/2000/09/xmldsig#}Reference'
                        )

        # Append digests to the DigestValue elements.
        for reference in references:
            if reference.attrib['URI'][1:] == body_id:
                dv = reference.find(
                        "{http://www.w3.org/2000/09/xmldsig#}DigestValue"
                        )
                dv.text = body_digest
            elif reference.attrib['URI'][1:] == timestamp_id:
                dv = reference.find(
                            "{http://www.w3.org/2000/09/xmldsig#}DigestValue"
                            )
                dv.text = timestamp_digest
        # Calculate signaturevalue
        infomessage = str(etree.tostring(signed_info), 'utf-8')
        signaturevalue = signature.calculate_signature_value(infomessage,
                                                             self.keyfile,
                                                             exclusive_=True)
        # Append signaturevalue to tree
        value = base64.b64encode(signaturevalue)
        SignatureValue = signature_.find(
                          "{http://www.w3.org/2000/09/xmldsig#}SignatureValue"
                        )
        SignatureValue.text = value
        self.log.debug("SignatureValue: {0}".format(value))
        # Return result as a string
        return etree.tostring(doc)


class SignQueue(object):
    """
    SignQueue class adds id's for parts of documents.

    @type queue: List
    @ivar queue: List containing given id's.
    """
    WSU_ID = ns_id('Id', wsuns)
    """WS-security utility id"""
    DS_DIGEST_VALUE = ns_id('DigestValue', dsns)
    """Digital signature digest value"""
    DS_REFERENCE = ns_id('Reference', dsns)
    """Digital signature reference value"""
    DS_TRANSFORMS = ns_id('Transforms', dsns)
    """Digital signature transform value"""
    def __init__(self):
        """ Initializes SignQueue class """
        self.queue = []

    def mark(self, element):
        """ Marks element with an unique id

        @type  element: L{_Element}
        @param element: Element to mark.
        @rtype: string
        @return: Id set to element.
        """
        unique_id = get_unique_id()
        element.set(self.WSU_ID, unique_id)
        return unique_id

    def push_and_mark(self, element):
        """ Marks element with and uniquq id and saves id to object.

        @type  element: L{lxml.etree._Element}
        @param element: Element to mark.
        """
        unique_id = get_unique_id()
        element.set(self.WSU_ID, unique_id)
        self.queue.append(unique_id)

    def insert_references(self, signed_info):
        """
        Inserts saved id's as references to signed info.

        @type  signed_info: L{lxml.etree._Element}
        @param signed_info: Signed info element from xml signature.
        """
        for element_id in self.queue:
            reference = etree.SubElement(signed_info, self.DS_REFERENCE,
                    {'URI': '#{0}'.format(element_id)})
            transforms = etree.SubElement(reference, self.DS_TRANSFORMS)
            set_algorithm(transforms, 'Transform', C14N)
            set_algorithm(reference, 'DigestMethod', XMLDSIG_SHA1)
            etree.SubElement(reference, self.DS_DIGEST_VALUE)


def get_unique_id():
    """Gets new unique id."""
    return 'id-{0}'.format(uuid4())


def set_algorithm(parent, name, value):
    """ Adds algorithm for element.

    @type  parent: L{lxml.etree._Element}
    @param parent: Element where algorithm tag is inserted.
    @type  name: string
    @param name: Type of the algoritm.
    @type  value: string
    @param value: Name of algorithm.
    """
    etree.SubElement(parent, ns_id(name, dsns), {'Algorithm': value})


def ensure_security_header(env, queue):
    """ Adds security header if its missing from env and adds id for timestamp.

    @type  env: L{lxml.etree._Element}
    @param env: Soap-envelope
    @type  queue: L{SignQueue}
    @param queue: Initialized SignQueue object.
    @rtype: L{lxml.etree._Element}
    @return: Ws-security header.
    """
    (header,) = HEADER_XPATH(env)
    security = SECURITY_XPATH(header)
    if security:
        for timestamp in TIMESTAMP_XPATH(security[0]):
            queue.push_and_mark(timestamp)
        return security[0]
    else:
        return etree.SubElement(header, ns_id('Security', wssens),
                {ns_id('mustUnderstand', envns): '1'}, NSMAP)
