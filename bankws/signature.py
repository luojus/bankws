"""
Xml-signature generation and verifying functions.

Usage:
To verify signature:
>>> result = validate(xml_string)
>>> if result:
        print 'Valid'
    else:
        print 'Failed to verify'

To sign xml message:
>>> signed_xml = sign(xml_string,"private_key.pem","certificate.x509")

Xml signing. http://www.w3.org/TR/xmldsig-core/
Needed external libraries:
    - LXML
    - PyCrypto
    - PyOpenSSL >0.12
"""
from io import StringIO, BytesIO
import base64
import hashlib
import logging

import Crypto.PublicKey.RSA as RSA
import Crypto.Hash.SHA as SHA
from Crypto.Signature import PKCS1_v1_5
from lxml.builder import ElementMaker
from lxml import etree
import OpenSSL

try:
    from bankws.certificate import check_revocation_status
except ImportError:
    from certificate import check_revocation_status
# Generate needed xml elements.
E = ElementMaker(namespace="http://www.w3.org/2000/09/xmldsig#",
                 nsmap={None: "http://www.w3.org/2000/09/xmldsig#"})

DOC = E.Signature
SIGNEDINFO = E.SignedInfo
CANONICALIZATIONMETHOD = E.CanonicalizationMethod
SIGNATUREMETHOD = E.SignatureMethod
REFERENCE = E.Reference
TRANSFORMS = E.Transforms
TRANSFORM = E.Transform
DIGESTMETHOD = E.DigestMethod
DIGESTVALUE = E.DigestValue
SIGNATUREVALUE = E.SignatureValue
KEYINFO = E.KeyInfo
X509DATA = E.X509Data
X509CERTIFICATE = E.X509Certificate


def validate(xml_string):
    """
    Validates given xml string

    @type  xml_string: string
    @param xml_string: xml string to verify
    @rtype: boolean
    @return: Result of verification.
    """
    log = logging.getLogger("bankws")
    try:
        tree = etree.fromstring(xml_string)
    except etree.XMLSyntaxError:
        log.error("Unable to parse xml-data.")
        return False

    result = tree.xpath("//ds:Signature",
                       namespaces={'ds': "http://www.w3.org/2000/09/xmldsig#"})

    signature = result[0] if len(result) > 0 else None
    if signature is None:
        log.error("Didn't find signature field")
        return False

    digestvalues = {}
    signed_info = None
    signaturevalue = None

    for element in signature.iter():
        if element.tag == "{http://www.w3.org/2000/09/xmldsig#}DigestValue":
            key = element.getparent().get('URI')
            digestvalues[key] = element.text
        if element.tag == "{http://www.w3.org/2000/09/xmldsig#}SignedInfo":
            signed_info = element
        if element.tag == "{http://www.w3.org/2000/09/xmldsig#}SignatureValue":
            log.debug("{0}: {1}".format(element.tag, element.text))
            signaturevalue = element.text

    # Get certificate from xml string
    certificate = get_certificate(xml_string)

    if certificate is None:
        log.error('Signed message but certificate is missing.')
        return False

    if signaturevalue is None:
        log.error("SignatureValue field is missing.")
        return False

    if signed_info is None:
        log.error("SignedInfo is missing.")
        return False

    # Values are base64 encoded so decode them
    certificate_data = base64.b64decode(bytes(certificate, 'utf-8'))
    signaturevalue = base64.b64decode(bytes(signaturevalue, 'utf-8'))

    algorithm = signed_info.xpath("//ds:CanonicalizationMethod[@Algorithm]",
                    namespaces={'ds': "http://www.w3.org/2000/09/xmldsig#"})

    if len(algorithm) > 0:
        comments = "#WithComments" in algorithm[0].get("Algorithm")
        exclusive = "xml-exc-c14n#" in algorithm[0].get("Algorithm")

    message = etree.tostring(signed_info)
    # Canonicalize message before calculations.
    canonicalizated_info = canonicalizate_message(str(message, 'utf-8'),
                                                  exclusive_=exclusive,
                                                  comments_=comments)

    #Calculate digests.
    for key, value in digestvalues.items():
        digest_value = ""
        if key == "":  # Whole document is used
            tree.remove(signature)
            xmlstring = str(etree.tostring(tree), 'utf-8')
            digest = calculate_digest(xmlstring, exclusive, comments)
            digest_value = str(base64.b64encode(digest.digest()), 'utf-8')
        else:
            result = tree.xpath("//*[@wsu:Id='" + key[1:] + "']",
                                namespaces=tree.nsmap)
            if len(result) == 1:
                xmlstring = str(etree.tostring(result[0]), 'utf-8')
                digest = calculate_digest(xmlstring, exclusive, comments)
                digest_value = str(base64.b64encode(digest.digest()), 'utf-8')

        if digest_value != value:
            log.error('{0}: Digest values differ.'.format(key))
            return False

    try:
        if check_revocation_status(certificate_data):
        # Certificate used to sign this message is on revocation list
            return False
    except ValueError:
        log.error("Unsupported certificate format.")
        return False

    # Generate certificate object from data found on x509data
    filetype = OpenSSL.crypto.FILETYPE_ASN1
    try:
        cert = OpenSSL.crypto.load_certificate(filetype, certificate_data)
    except OpenSSL.crypto.Error as e:
        log.exception(e)
        return False

    # Verify signature
    try:
        OpenSSL.crypto.verify(
            cert, signaturevalue, bytes(canonicalizated_info, 'utf-8'), 'sha1'
            )
    except OpenSSL.crypto.Error as e:
        log.exception(e)
        return False

    return True


def sign(xml_string, private_key, certificate, xml_declaration_=False):
    """
    Signs xml message with dsig algorithm.

    @type  xml_string: string
    @param xml_string: Xml text to sign
    @type  private_key: string
    @param private_key: Name of the file containing private key.
    @type  certificate: string
    @param certificate: Name of the file containing X509v3 certificate.
    @type  xml_declaration_: boolean
    @param xml_declaration:  Add xml declaration to xml string.
    @rtype: string
    @return: Xml string signed with private key.
    @raise IOError: In case of failing open private key or certificate file.
    @raise ValueError: In case of private key being in unsupported format.
    """
    # Test that xml can be parsed.
    try:
        e = etree.fromstring(xml_string)
    except etree.XMLSyntaxError:
        raise RuntimeError("Malformatted xml string")
    xml_string = str(etree.tostring(e), 'utf-8')
    signature = generate_xml_signature(xml_string, private_key, certificate)
    e.append(signature)
    return etree.tostring(e,
                          xml_declaration=xml_declaration_,
                          encoding="UTF-8",
                          pretty_print=False)


def get_certificate(xml_string):
    """
    Gets certificate from xml_string.

    @type  xml_string: bytes
    @param xml_string: XML-string containing certificate data.
    @rtype: string
    @return: Base64 encoded Certificate data or
             None if certificate is not found.
    """
    WSSE = ("http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss"
            "-wssecurity-secext-1.0.xsd")
    DSIG = "http://www.w3.org/2000/09/xmldsig#"

    tree = etree.fromstring(xml_string)
    keyinfo = tree.xpath("//ds:KeyInfo",
                       namespaces={'ds': DSIG})
    if len(keyinfo) > 0:
        reference = keyinfo[0].xpath("//wsse:Reference",
                                     namespaces={'wsse': WSSE})
        if len(reference) > 0:
            # Certificate is in BinarySecurityToken element.
            bst = tree.xpath("//wsse:BinarySecurityToken",
                             namespaces=tree.nsmap)
            if len(bst) > 0:
                return bst[0].text
        else:
            # Certificate is in X509Certificate element
            certificate = keyinfo[0].xpath("//ds:X509Certificate",
                              namespaces={'ds': DSIG})
            if len(certificate) > 0:
                return certificate[0].text
    return None


def canonicalizate_message(xml_string, exclusive_=False, comments_=False):
    """ Canonicalizates given xml_string

    @type  xml_string: string
    @param xml_string: Xml string to canonicalizate
    @type  exclusive_: boolean
    @param exclusive_: Use exclusive canonicalization
    @type  comments_: boolean
    @param comments_: Use with_comments mode in canonicalization.
    @rtype: string
    @return: Canonicalizated version of xml_string
    """
    file_object = StringIO(xml_string)  # Generate file like object from string
    tree = etree.parse(file_object)
    file_object = BytesIO()  # Empty file object to write canonicalizated xml
    tree.write_c14n(file_object, with_comments=comments_, exclusive=exclusive_)
    message = str(file_object.getvalue(), 'utf-8')
    return message


def calculate_digest(xml_string, exclusive_=False, comments_=False):
    """
    Calculates message digest for signing

    @type xml_string: string
    @param xml_string: Xml text
    @rtype: L{Digest}
    @return: sha-1 digest of the message
    """
    message = canonicalizate_message(xml_string, exclusive_, comments_)
    digest = hashlib.sha1(bytes(message, 'utf-8'))
    return digest


def calculate_signature_value(xml_string, private_key, exclusive_=False,
                              comments_=False):
    """
    Calculates rsa-sha1 signaturevalue for signed xml

    @type  xml_string: bytes or string
    @param xml_string: Signed info element as a string.
    @type  private_key: string
    @param private_key: Private RSA-key filename
    @type  exclusive_: boolean
    @param exclusive_: Use exclusive canonicalization
    @type  comments_: boolean
    @param comments_: Use with_comments-style canonicalization.
    @raise IOError: If the private key can't be read from file.
    @raise ValueError: If PyCrypto can't import RSA-key
    @rtype: string
    @return: Calculated signaturevalue as a raw string.
    """
    log = logging.getLogger('bankws')
    canonicalizated_info = canonicalizate_message(xml_string,
                                                  exclusive_,
                                                  comments_)

    try:
        with open(private_key, 'rb') as f:
            content = f.read()
    except EnvironmentError as e:
        log.exception(e)
        raise IOError("Failed to open file {0}".format(private_key))

    try:
        pkey = RSA.importKey(content)
    except ValueError as e:
        log.exception(e)
        raise

    info_digest = SHA.new(canonicalizated_info.encode('utf-8'))
    signer = PKCS1_v1_5.new(pkey)
    signaturevalue = signer.sign(info_digest)
    return signaturevalue


def generate_xml_signature(xml_string, private_key, X509certificate):
    """ Generates xml signature

    @type  xml_string: String
    @param xml_string: String to sign
    @type  X509certificate: string
    @param X509certificate: Certificate filename
    @type  private_key: string
    @param private_key: RSA private key filename
    @raise IOError: In case of failing open private key or certificate file.
    @raise ValueError: In case of private key being in unsupported format.
    @rtype: L{lxml.etree._Element}
    @return: Signature element.
    """
    log = logging.getLogger('bankws')
    log.info("Generating signature.")
    # Canonicalization algorithms
    C14NWITHCOMMENTS = ("http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
                        "#WithComments")
    # Signature algorithms
    RSASHA1 = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
    # Transform algorithms
    ENVELOPED = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
    # Digest algorithms
    SHA1 = "http://www.w3.org/2000/09/xmldsig#sha1"
    digest = calculate_digest(xml_string, comments_=True)
    info = \
    SIGNEDINFO(
        CANONICALIZATIONMETHOD(Algorithm=C14NWITHCOMMENTS),
        SIGNATUREMETHOD(Algorithm=RSASHA1),
        REFERENCE(
            TRANSFORMS(
                TRANSFORM(Algorithm=ENVELOPED)
            ),
            DIGESTMETHOD(Algorithm=SHA1),
            DIGESTVALUE(str(base64.b64encode(digest.digest()), 'utf-8')),
            URI=""
        ),
    )

    tree = etree.fromstring(xml_string)
    # Append info to original xml string so info element gets correct
    # namespace declarations.
    tree.append(info)

    info_message = str(etree.tostring(info), 'utf-8')
    log.debug("Signature Info part: {0}".format(info_message))
    signaturevalue = calculate_signature_value(info_message,
                                               private_key,
                                               comments_=True)

    try:
        with open(X509certificate, 'rb') as f:
            content = f.read()
    except EnvironmentError as e:
        log.exception(e)
        raise IOError("Failed to open file {0}".format(X509certificate))

    signature = \
    DOC(
        SIGNATUREVALUE(str(base64.b64encode(signaturevalue), 'utf-8')),
        KEYINFO(
            X509DATA(
                X509CERTIFICATE(str(base64.b64encode(content), 'utf8'))
            )
        )
    )

    signature.insert(0, info)
    return signature
