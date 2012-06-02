'''
Timehelper module is used to generate timestamps in correct format.

Usage:
>>> import timehelper
>>> timehelper.get_timestamp()

Localtimezone class copied from http://docs.python.org/library/datetime.html
'''
import time as _time
from datetime import tzinfo, timedelta, datetime

STDOFFSET = timedelta(seconds=-_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds=-_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET


class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return timedelta(0)

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day, dt.hour,
              dt.minute, dt.second, dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0


def get_timestamp(with_microseconds=True):
    """ Gets current time in ISO8601 format

    @type  with_microseconds: boolean
    @param with_microseconds: Return value with or without microseconds.
    @rtype: string
    @return: Current time in ISO8601 format
    """
    now = datetime.now(LocalTimezone())
    if not with_microseconds:
        now = now.replace(microsecond=0)
    return now.isoformat('T')
