'''Bank module contains bank class and pre-made Bank-object for Osuuspankki.'''


class Bank():
    """ Bank class contains urls and BIC for the banks Web service."""
    def __init__(self, BIC, url, test_url=None, id_url=None, id_test_url=None):
        """ Initializes Bank class.

        @type  BIC: string
        @param BIC: Bank Identifier Code
        @type  url: string
        @param url: url for production web services.
        @type  test_url: string
        @param test_url: Url for web services test environment.
        @type  id_url: string
        @param id_url: Url for production identification service.
        @type  id_test_url: string
        @param id_test_url: Url for identification service test environment.
        """
        self.BIC = BIC
        self.wsdl_url = url
        self.wsdl_test_url = test_url
        self.id_url = id_url
        self.id_test_url = id_test_url

OP = Bank("OKOYFIHH",
          "https://wsk.op.fi/wsdl/MaksuliikeWS.xml",
          "https://wsk.asiakastesti.op.fi/wsdl/MaksuliikeWS.xml",
          "https://wsk.op.fi/wsdl/MaksuliikeCertService.xml",
          "https://wsk.asiakastesti.op.fi/wsdl/MaksuliikeCertService.xml")
""" Information needed for Osuuspankki Web Services """
