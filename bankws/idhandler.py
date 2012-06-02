'''
IDHandler module offers ways to get persistent object for handling request id's

Sample usage:
    >>> import idhandler
    >>> obj = idhandler.get_object()
To get new request id:
    >>> obj.next_value()
Before quitting save object back to file:
    >> idhandler.save_object()
'''
import pickle
import os
import logging
from datetime import date
log = logging.getLogger("bankws")


class __RequestId:
    """ Simple class for holding id value.

    Current ID format is YYYYMMDDXXXXX where x is number between [00001-99999]
    """

    def __init__(self, initial_value=0):
        """ Constuctor for RequestId class """
        self._value = initial_value
        self._date = date.today()

    def next_value(self):
        """ Gets value for request id """
        if self._date != date.today():
            self._value = 0
            self._date = date.today()
        self._value += 1
        value = self._date.strftime("%Y%m%d") + "{:05}".format(self._value)
        return value


def get_object():
    """ Gets RequestId object """
    try:
        with open('resources/requestid.dat', 'rb') as idfile:
            obj = pickle.load(idfile)
    except EnvironmentError:
        obj = __RequestId()
    except ImportError:
        # If user moves requestid.dat, trying to load object
        # can cause ImportError
        obj = __RequestId()
    return obj


def save_object(obj):
    """ Saves object back to file

    @type  obj: __RequestId
    @param obj: Object to be saved
    """
    try:
        with open('resources/requestid.dat', 'wb') as idfile:
            pickle.dump(obj, idfile)
    except EnvironmentError:
        if not os.path.exists("resources"):
            try:
                os.mkdir("resources")
            except OSError as e:
                log.error(e)
                log.error("Unable to create directory for requestid object.")
                log.error("This means that you won't get unique"
                          " id's in to the requests.")
            else:
                try:
                    with open('resources/requestid.dat', 'wb') as idfile:
                        pickle.dump(obj, idfile)
                except EnvironmentError as e:
                    log.error(e)
                    log.error("Unable to save requestid object to disk.")
