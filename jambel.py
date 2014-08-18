#!/usr/bin/env python
# Sebastian Rahlf <sebastian.rahlf@jambit.com>

"""
Interface to jambit's project traffic lights.

To remote control a Jambel, simply run this script::

    jambel.py ampel3.dev.jambit.com --debug green=on yellow=blink red=off
    jambel.py ampel3.dev.jambit.com:10001 reset

"""

import argparse
import functools
import logging
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

    def __repr__(self):  # pragma: no cover
        return '<%s module=%d>' % (self.__class__.__name__, self._no)

    def on(self, duration=None):
        """
        :param duration: on duration (in ms)
        """
        self._jambel._on(self._no, duration)  # pylint: disable=W0212

    def off(self):
        self._jambel._off(self._no)

    def blink(self, inverse=False):
        self._jambel._blink(self._no, inverse)  # pylint: disable=W0212

    def flash(self):
        self._jambel._flash(self._no)  # pylint: disable=W0212

    def status(self):
        return self._jambel.status(raw=True)[self._no-1]

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

    _logger = logging.getLogger('Jambel')

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
            return False          # re-raise the exception

    def __repr__(self):  # pragma: no cover
        return '<%s at %s:%s>' % (self.__class__.__name__, self.host, self.port)

    def _send(self, cmd):
        """
        Sends a single command to the Jambel.
        :type cmd: string
        :return: Jambel's response
        """
        self._logger.debug('Connecting to %s:%s...' % (self.host, self.port))
        conn = telnetlib.Telnet(self.host, self.port)
        value = ('%s\n' % cmd).encode('utf-8')
        self._logger.debug('Send command %r.' % value)
        conn.write(value)
        response = conn.read_until('\n'.encode('utf-8')).decode('utf-8')
        self._logger.debug('Received response %r.' % response)
        return response

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


def main(args=None):
    """
    CLI interface. Try ``main(['-h'])`` to find out more.
    """
    single = ['status', 'reset', 'version', 'test']
    multi = ['green', 'yellow', 'red']
    allowed_values = ['on', 'off', 'blink', 'blink_inverse', 'flash']

    def addr(string):
        parts = string.split(':')
        if len(parts) == 1:
            return parts[0], Jambel.DEFAULT_PORT
        if len(parts) == 2:
            try:
                return parts[0], int(parts[1])
            except ValueError:
                msg = "Port needs to be integer!"
                raise argparse.ArgumentTypeError(msg)
        msg = "Address format: HOST[:PORT]!"
        raise argparse.ArgumentTypeError(msg)

    def command(string):
        parts = string.split('=')
        command = parts[0].lower()
        if command in single:
            return command, None
        if command in multi:
            if len(parts) != 2:
                msg = "Command needs format %s=VALUE!" % command
                raise argparse.ArgumentTypeError(msg)
            value = parts[1]
            if value not in allowed_values:
                msg = "Value for command %s needs to be one of %r!" % (command, allowed_values)
                raise argparse.ArgumentTypeError(msg)
            return command, value
        msg = "Command not found!" % command
        raise argparse.ArgumentTypeError(msg)

    parser = argparse.ArgumentParser(description='Remote control a Jambel.')
    parser.add_argument('addr', metavar='HOST', type=addr, help='Jambel address (format: <host>[:<port>])')
    parser.add_argument('commands', metavar='CMD', type=command, nargs='+',
        help='A command for the jambel to execute. Multiple commands are executed in order')
    parser.add_argument('--debug', action='store_true', default=False,
        help='Turn debugging on')
    parser.add_argument('--red-on-top', dest='green_position', action='store_const', const=BOTTOM, default=TOP,
        help='Red light is on top (default: bottom)')

    args = parser.parse_args(args)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    jambel = Jambel(args.addr[0], args.addr[1], green=args.green_position)
    for cmd, value in args.commands:
        if cmd in single:
            fnc = getattr(jambel, cmd)
            fnc()
        else:
            light = getattr(jambel, cmd)
            fnc = {
                'on': light.on,
                'off': light.off,
                'blink': light.blink,
                'blink_inverse': functools.partial(light.blink, inverse=True),
                'flash': light.flash
            }[value]
            fnc()


if __name__ == '__main__':  # pragma: no cover
    # main(['ampel3.dev.jambit.com', 'green=on', 'yellow=blink', 'red=off', '--debug'])
    # main(['ampel3.dev.jambit.com', 'reset'])
    main()
