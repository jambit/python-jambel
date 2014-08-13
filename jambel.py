
"""
Interface to jambit's project traffic lights.

Sebastian Rahlf <sebastian.rahlf@jambit.com>
"""

import telnetlib
import re


OFF = 0
ON = 1
BLINK = 2
FLASH = 3
BLINK_INVERSE = 4

TOP = 'top'
BOTTOM = 'bottom'

ALL_OFF = [OFF, OFF, OFF]
PANIC = [FLASH, FLASH, FLASH]


class LightModule(object):

    """
    A single light module of a Jambel.
    """

    def __init__(self, jambel, no):
        """
        :type jambel: Jambel
        :type no: int
        """
        self._jambel = jambel
        self._no = no

    def __repr__(self):
        return '<%s module=%d>' % (self.__class__.__name__, self._no)

    def on(self, duration=None):
        """
        :param duration: on duration (in ms)
        """
        self._jambel._on(self._no, duration)

    def off(self):
        self._jambel._off(self._no)

    def blink(self, inverse=False):
        self._jambel._blink(self._no, inverse)

    def flash(self):
        self._jambel._flash(self._no)

    def status(self):
        return self._jambel.status(raw=True)[self._no]

    def blink_time(self, on, off):
        """
        :param on: on time (in ms)
        :param off: off time (in ms)
        """
        self._jambel.set_blink_time(self._no, on, off)


class Jambel(object):

    """
    Interface to a jambit traffic light. ::

        >>> from jambel import Jambel, ALL_OFF
        >>> jambel = Jambel('traffic.jambit.com')
        >>> jambel.green.on()
        >>> jambel.yellow.blink()
        >>> jambel.red.flash()
        >>> jambel.status()
        [1, 2, 3]
        >>> jambel.set(ALL_OFF)

    Some lights have the green light module at the bottom. For those you need to instantiate the Jambel object using ::

        >>> from jambel import BOTTOM
        >>> jambel = Jambel('traffic.jambit.com', green=BOTTOM)
        >>> jambel.green.on()

    """

    DEFAULT_PORT = 10001

    def __init__(self, host, port=DEFAULT_PORT, green=TOP):
        """
        :param host: Jambel host name/IP address
        :param port: Jambel port number
        :param green: ``BOTTOM`` if green module is at the bottom, ``TOP`` otherwise
        """
        self.host, self.port = host, port
        self._green_first = green == BOTTOM
        order = range(1, 4) if self._green_first else range(3, 0, -1)
        self.green, self.yellow, self.red = [LightModule(self, no) for no in order]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:  # an exception has occurred
            return False          # reraise the exception

    def __repr__(self):
        return '<%s at %s:%s>' % (self.__class__.__name__, self.host, self.port)

    def _send(self, cmd):
        """
        Sends a single command to the Jambel.
        :type cmd: string
        :return: Jambel's response
        """
        conn = telnetlib.Telnet(self.host, self.port)
        conn.write(('%s\n' % cmd).encode('utf-8'))
        return conn.read_until('\n'.encode('utf-8')).decode('utf-8')

    def _on(self, module, duration=None):
        if duration:
            if duration > 65000:
                raise ValueError('Max duration 65000 ms!')
            self._send('set=%i,%i' % (module, duration))
        else:
            self._send('set=%i,on' % module)

    def _off(self, module):
        self._send('set=%i,off' % module)

    def _blink(self, module, inverse=False):
        self._send('set=%i,%s' % (module, 'blink' if not inverse else 'blink_invers'))

    def _flash(self, module):
        self._send('set=%i,flash' % module)

    def reset(self):
        self._send('reset')

    def set_blink_time_on(self, duration):
        self._send('blink_time_on=%i' % duration)

    def set_blink_time_off(self, duration):
        self._send('blink_time_off=%i' % duration)

    def set_blink_time(self, module, on_time, off_time):
        self._send('blink_time=%i,%i,%i' % (module, on_time, off_time))

    _status_reg = re.compile(r'^status=(\d+(?:,\d+)*)')

    def status(self, raw=False):
        """
        Will return a list of status codes for the light modules. ::

            >>> jambel = Jambel('ampel5.dev.jambit.com')
            >>> green, yellow, red = jambel.status()
            >>> if green == BLINK:
            ...     print 'green light is blinking!'

        Status code are:

        * OFF
        * ON
        * BLINK
        * FLASH
        * BLINK_INVERSE

        If you want to see which module has which status without mapping it to position of the individualcolours,
        use ``raw=True``.

        :param raw: returns list of status codes as it comes from the Jambel, i.e. without ordering by light colour
        :return: list of status codes for each light module ([green, yellow, red])
        """
        result = self._send('status')
        try:
            values = self._status_reg.search(result).group(1)
            codes = list(map(int, values.split(',')))[:3]
            if not raw and not self._green_first:
                codes.reverse()
            return codes
        except (TypeError, ValueError):
            raise TypeError('Could not parse jambel status %r!' % result)

    def set(self, status):
        """
        Sets status for all light modules. See :meth:`status` for available status flags.

        :param status: list status codes for each light module ([green, yellow, red])
        """
        codes = list(map(str, status))
        if not self._green_first:
            codes.reverse()
        self._send('set_all=%s' % ','.join(codes + ['0']))

    def test(self):
        return self._send('test')

    def version(self):
        return self._send('version')


if __name__ == '__main__':
    import time
    with Jambel('ampel3.dev.jambit.com') as jambel:
        print(jambel.version())
        jambel.green.blink_time(100, 200)
        jambel.yellow.blink_time(130, 300)
        jambel.red.blink_time(210, 100)
        jambel.green.blink()
        jambel.yellow.blink()
        jambel.red.blink()
        jambel.set(ALL_OFF)
        time.sleep(10)
        print(repr(jambel.status()))