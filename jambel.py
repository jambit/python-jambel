
"""
Sebastian Rahlf <sebastian.rahlf@jambit.com>
"""
import re

__all__ = ['Jambel']

import telnetlib
import re


OFF = 0
ON = 1
BLINK = 2
FLASH = 3
BLINK_INVERSE = 4

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

    def on(self, time=None):
        """
        :param time: on time (in ms)
        """
        self._jambel._on(self._no, time)

    def off(self):
        self._jambel._off(self._no)

    def blink(self, inverse=False):
        self._jambel._blink(self._no, inverse)

    def flash(self):
        self._jambel._flash(self._no)

    def status(self):
        return self._jambel.status()[self._no]

    def blink_time(self, on, off):
        """
        :param on: on time (in ms)
        :param off: off time (in ms)
        """
        self._jambel.set_blink_time(self._no, on, off)


class Jambel(object):

    """
    Interface to a jambit traffic light. ::

        >>> jambel = Jambel('traffic.jambit.com')
        >>> jambel.green.on()
        >>> jambel.yellow.blink()
        >>> jambel.red.flash()
        >>> jambel.status()
        [1, 2, 3]
        >>> jambel.set(ALL_OFF)

    """

    DEFAULT_PORT = 10001

    def __init__(self, host, port=DEFAULT_PORT):
        self._conn = telnetlib.Telnet(host, port)
        self.green = LightModule(self, 1)
        self.yellow = LightModule(self, 2)
        self.red = LightModule(self, 3)

    def __del__(self):
        if hasattr(self, '_conn'):
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print exc_type, exc_val, exc_tb

    def _send(self, cmd):
        self._conn.write('%s\n' % cmd)
        return self._conn.read_until('\n')

    def _on(self, module, time=None):
        if time:
            if time > 65000:
                raise ValueError('Max value 65000 ms!')
            self._send('set=%i,%i' % (module, time))
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

    def set_blink_time_on(self, time):
        self._send('blink_time_on=%i' % time)

    def set_blink_time_off(self, time):
        self._send('blink_time_off=%i' % time)

    def set_blink_time(self, module, on_time, off_time):
        self._send('blink_time=%i,%i,%i' % (module, on_time, off_time))

    _status_reg = re.compile(r'^status=(\d+(?:,\d+)*)')

    def status(self):
        result = self._send('status')
        try:
            codes = self._status_reg.search(result).group(1)
            return map(int, codes.split(','))[:3]
        except (TypeError, ValueError):
            raise TypeError('Could not parse jambel status %r!' % result)

    def set(self, status):
        codes = map(str, status) + ['0']
        self._send('set_all=%s' % ','.join(codes))

    def test(self):
        return self._send('test')

    def version(self):
        return self._send('version')


if __name__ == '__main__':
    import time
    with Jambel('ampel3.dev.jambit.com') as jambel:
        print jambel.version()
        jambel.green.blink_time(100, 200)
        jambel.yellow.blink_time(130, 300)
        jambel.red.blink_time(210, 100)
        jambel.green.blink()
        jambel.yellow.blink()
        jambel.red.blink()
        jambel.set(ALL_OFF)
        # time.sleep(10)
        print repr(jambel.status())