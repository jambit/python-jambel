#!/usr/bin/env python
# Sebastian Rahlf <sebastian.rahlf@jambit.com>

"""
Interface to jambit's project traffic lights.

COMMANDS:

  status       - Will return a list of status codes for the light modules as JSON.
  version      - Returns version string.
  reset        - Switches all lights off and sets blink times to default values.
  test         - Tests communication without disturbing anything
  <col>=<stat> - Set status for one colour module where
                 <col> is one of [green, yellow, red]
                 <stat> is one of [on, off, blink, blink_inverse, flash]

EXAMPLES:

To remote control a Jambel, simply run this script::

    jambel.py ampel3.dev.jambit.com --debug green=on yellow=blink red=off
    jambel.py ampel1.dev.jambit.com:10001 reset green=flash

"""

import argparse
import functools
import logging
import telnetlib
import re

__version__ = '0.1.1'

OFF = 0
ON = 1
BLINK = 2
FLASH = 3
BLINK_INVERSE = 4

TOP = 'top'
BOTTOM = 'bottom'

GREEN = 'green'
YELLOW = 'yellow'
RED = 'red'

ALL_OFF = [OFF, OFF, OFF]
PANIC = [FLASH, FLASH, FLASH]


class LightModule(object):

    """
    A single light module of a Jambel.
    """

    def __init__(self, jambel, colour):
        """
        :type jambel: Jambel
        :type colour: str
        """
        self._jambel = jambel
        self.colour = colour

    def __repr__(self):  # pragma: no cover
        return '<%s module=%s>' % (self.__class__.__name__, self.colour)

    def on(self, duration=None):
        """
        :param duration: on duration (in ms)
        """
        return self._jambel._on(self.colour, duration)  # pylint: disable=W0212

    def off(self):
        return self._jambel._off(self.colour)

    def blink(self, inverse=False):
        return self._jambel._blink(self.colour, inverse)  # pylint: disable=W0212

    def flash(self):
        return self._jambel._flash(self.colour)  # pylint: disable=W0212

    def status(self):
        return self._jambel.status()[self.colour]

    def blink_time(self, on, off):
        """
        :param on: on time (in ms)
        :param off: off time (in ms)
        """
        return self._jambel.set_blink_time(self.colour, on, off)


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
        self._order = [GREEN, YELLOW, RED] if green == BOTTOM else [RED, YELLOW, GREEN]

        self.green = LightModule(self, GREEN)
        self.yellow = LightModule(self, YELLOW)
        self.red = LightModule(self, RED)

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

    def _on(self, colour, duration=None):
        module = self._get_module_no(colour)
        if duration:
            if duration > 65000:
                raise ValueError('Max duration 65000 ms!')
            return self._send('set=%i,%i' % (module, duration))
        else:
            return self._send('set=%i,on' % module)

    def _off(self, colour):
        module = self._get_module_no(colour)
        return self._send('set=%i,off' % module)

    def _blink(self, colour, inverse=False):
        module = self._get_module_no(colour)
        return self._send('set=%i,%s' % (module, 'blink' if not inverse else 'blink_invers'))

    def _flash(self, colour):
        module = self._get_module_no(colour)
        return self._send('set=%i,flash' % module)

    def reset(self):
        """
        Switches all lights off and sets blink times to default values.
        :return:
        """
        return self._send('reset')

    def set_blink_time_on(self, duration):
        """
        Sets time lights are ON for all modules.
        :param duration: time in ms
        """
        return self._send('blink_time_on=%i' % duration)

    def set_blink_time_off(self, duration):
        """
        Sets time lights are OFF for all modules.
        :param duration: time in ms
        """
        return self._send('blink_time_off=%i' % duration)

    def set_blink_time(self, colour, on_time, off_time):
        """
        Sets time lights are ON and OFF for specific module.
        :param colour: coulour of light module
        :param on_time: time in ms
        :param off_time: time in ms
        """
        module = self._get_module_no(colour)
        return self._send('blink_time=%i,%i,%i' % (module, on_time, off_time))

    _status_reg = re.compile(r'^status=(\d+(?:,\d+)*)')

    def status(self):
        """
        Will return a list of status codes for the light modules. ::

            >>> jambel = Jambel('ampel5.dev.jambit.com')
            >>> status = jambel.status()
            >>> if status[GREEN] == BLINK:
            ...     print('green light is blinking!')

        Status code are:

        * OFF
        * ON
        * BLINK
        * FLASH
        * BLINK_INVERSE

        :return: dict with light colours mapping to their status codes
        """
        result = self._send('status')
        try:
            values = self._status_reg.search(result).group(1)
            codes = list(map(int, values.split(',')))[:3]
            return dict(zip(self._order, codes))
        except (TypeError, ValueError):
            raise TypeError('Could not parse jambel status %r!' % result)

    def set(self, status):
        """
        Sets status for all light modules. See :meth:`status` for available status flags.

        :param status: list status codes for each light module ([green, yellow, red])
        """
        codes = list(map(str, status))
        if not self._order[0] == GREEN:
            codes.reverse()
        return self._send('set_all=%s' % ','.join(codes + ['0']))

    def test(self):
        """
        Tests communication without disturbing anything
        :return: ``True`` if Jambel answered with "OK", ``False`` otherwise.
        """
        return self._send('test').strip() == 'OK'

    def version(self):
        """
        Returns version string.
        """
        return self._send('version')

    def _get_module_no(self, colour):
        """Returns number of light module"""
        return self._order.index(colour) + 1


def main(args=None):
    """
    CLI interface. Try ``main(['-h'])`` to find out more.
    """
    single = ['status', 'reset', 'version', 'test']
    multi = ['green', 'yellow', 'red']
    allowed_values = ['on', 'off', 'blink', 'blink_inverse', 'flash']
    chatty = ['status', 'version', 'test']

    def addr(string):
        parts = string.split(':')
        if not parts[0]:
            msg = "Host is required!"
            raise argparse.ArgumentTypeError(msg)
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
        _cmd = parts[0].lower()
        if _cmd in single:
            if len(parts) > 1:
                msg = "Command %s needs has no parameter!" % _cmd
                raise argparse.ArgumentTypeError(msg)
            return _cmd, None
        if _cmd in multi:
            if len(parts) != 2:
                msg = "Command needs format %s=VALUE!" % _cmd
                raise argparse.ArgumentTypeError(msg)
            val = parts[1]
            if val not in allowed_values:
                msg = "Value for command %s needs to be one of %r!" % (_cmd, allowed_values)
                raise argparse.ArgumentTypeError(msg)
            return _cmd, val
        msg = "Command %s not found!" % _cmd
        raise argparse.ArgumentTypeError(msg)

    parser = argparse.ArgumentParser(description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('addr', metavar='HOST', type=addr, help='Jambel address (format: <host>[:<port>])')
    parser.add_argument('commands', metavar='CMD', type=command, nargs='+',
        help='A command for the jambel to execute. Multiple commands are executed in order. See COMMANDS '
            'for more details.')
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
        else:
            light = getattr(jambel, cmd)
            fnc = {
                'on': light.on,
                'off': light.off,
                'blink': light.blink,
                'blink_inverse': functools.partial(light.blink, inverse=True),
                'flash': light.flash
            }[value]
        result = fnc()
        if cmd in chatty:
            print(result)


if __name__ == '__main__':  # pragma: no cover
    # main(['ampel3.dev.jambit.com', 'green=on', 'yellow=blink', 'red=off', '--debug'])
    # main(['ampel3.dev.jambit.com', 'reset'])
    main()
