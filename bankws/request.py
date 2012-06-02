'''Request module contains Request-class that is used as a base
class for different kind xml-requests.
'''
import base64


class Request:
    '''
    Baseclass for request objects.
    '''
    def __init__(self, id_, environment):
        '''
        Constructor

        @type  id: int
        @param id: Osuuspankki CustomerId (10 numbers)
        @type  environment: string
        @param environment: TEST or PRODUCTION
        '''
        self._id = str(id_)
        if environment.upper() in ["TEST", "PRODUCTION"]:
            self._environment = environment.upper()
        else:
            raise RuntimeError("Unknown environment")

    def get_request(self):
        """
        Gets base64 encoded presentation of request xml.
        """
        try:
            return base64.b64encode(self.text)
        except AttributeError:
            return None

    def __str__(self):
        try:
            return self.text.decode('utf-8')
        except AttributeError:
            return "Text attribute is empty."
