'''Certificate module contains functions that check certificate revocation
status and is certifice still valid.

Usage:
    # Checks if certificate is on revocation list
    >>> check_revocation_status(certificate)
    # Checks can certificate be renewed
    >>> check_renewable_status(certificate)

external libraries::
    - PyOpenSSL
'''
import datetime
import os
import logging
import urllib
from urllib import request

from OpenSSL import crypto

log = logging.getLogger("bankws")


def check_revocation_status(certificate):
    """
    Checks bank certificate revocation status.

    @type  certificate: (byte)String
    @param certificate: Certificate
    @rtype: boolean
    @return: Have asked certificate been revocated.
    """
    # Check if crl file exists
    renew = False

    if os.path.isfile('resources/OP-Pohjola-ws.crl'):
        modified = os.path.getmtime('resources/OP-Pohjola-ws.crl')
        modify_time = datetime.datetime.fromtimestamp(modified)
        difference = datetime.datetime.today() - modify_time
        if difference.days > 0:
            renew = True
    else:
        renew = True

    if renew:
        url = "http://wsk.op.fi/crl/ws/OP-Pohjola-ws.crl"
        try:
            with open('resources/OP-Pohjola-ws.crl', 'wb') as f:
                r = request.urlopen(url).read()
                f.write(r)
        except urllib.error.URLError as e:
            log.error(e)
            print("Unable to update/download new certificate revocation list.")
            if not os.path.exists('resources/OP-Pohjola-ws.crl'):
                # Unable to test against anything
                return False

        except EnvironmentError as e:
            if not os.path.exists("resources"):
                try:
                    os.mkdir("resources")
                except OSError as e:
                    log.error(e)
                    log.error("Unable to create directory for revocation"
                              " list.")
                    log.error("This means that certificate bank is using"
                              "won't be checked.")
                    return False
                else:
                    try:
                        with open('resources/OP-Pohjola-ws.crl', 'wb') as f:
                            r = request.urlopen(url).read()
                            f.write(r)
                    except EnvironmentError as e:
                        log.error(e)
                        log.error("Unable to crl to disk.")
                        log.error("This means that certificate that bank is"
                                  " using won't be checked.")
                        return False

    with open('resources/OP-Pohjola-ws.crl', 'rb') as f:
        crl = f.read()
    op_crl = crypto.load_crl(crypto.FILETYPE_ASN1, crl)
    revoked = op_crl.get_revoked()
    try:
        certificate = crypto.load_certificate(crypto.FILETYPE_ASN1,
                                              certificate)
    except crypto.Error:
        raise ValueError("Unable to load certificate")

    sn = certificate.get_serial_number()
    for cert in revoked:
        if cert.get_serial() == sn:
            return True
    return False


def check_renewable_status(certificate):
    """
    Checks can given certificate renew.

    @type certificate: string
    @param certificate: Certificate filename.
    @rtype: boolean
    @return: Is certificate renewable or not.
    @raise EnvironmentError: if file is not found.
    @raise RuntimeError: If certificate is expired.
    """
    cert = ""
    try:
        with open(certificate, 'rb') as f:
            cert = f.read()
    except EnvironmentError:
        print('Unable to open certificate file')
        raise

    x509object = crypto.load_certificate(crypto.FILETYPE_ASN1, cert)
    if x509object.has_expired():
        raise RuntimeError("Certificate expired.")
    last_valid_date = x509object.get_notAfter()
    year = int(last_valid_date[0:4])
    month = int(last_valid_date[4:6])
    day = int(last_valid_date[6:8])
    last_date = datetime.date(year, month, day)
    if (last_date - datetime.date.today()) < datetime.timedelta(days=60):
        return True
    else:
        return False
