
import telnetlib
import pytest

import jambel as _jambel


class TelnetMock(object):

    """
    Class mocking the most relevant methods of :class:`telnetlib.Telnet`. Interactions are reported back to the
    a :class:`MockConnectionFactory` instance for later reference.
    """

    def __init__(self, mock):
        self.closed = False
        self.mock = mock

    def write(self, cmd):
        self.mock.last_cmd = cmd

    def read_until(self, *args, **kwargs):
        return self.mock.response

    def close(self):
        self.closed = True


class MockConnectionFactory(object):

    """
    Returns instantiated :class:`TelnetMock` objects. This mechanism is used in order to have one instance per test,
    which can reliably be queried for mocked response and last command sent.

    Using a global reference instance would not work with parallel tests, for instance.
    """

    def __init__(self):
        self._lastcmd = []
        self._response = None
        self.last_addr = None

    def __call__(self, host, port):
        self.last_addr = (host, port)
        return TelnetMock(self)

    @property
    def last_cmd(self):
        return self._lastcmd[-1].decode('UTF-8')
    @last_cmd.setter
    def last_cmd(self, value):
        self._lastcmd.append(value)

    def history(self, strip=True):
        """
        Returns a list of previously called commands with the most recent first.
        :param strip: run strip() on each command to get rid of ``\r\n``
        """
        cmds = map(lambda x: x.decode('UTF-8'), self._lastcmd)
        history = list(map(lambda x: x.strip(), cmds) if strip else cmds)
        return history[::-1]

    @property
    def response(self):
        return self._response
    @response.setter
    def response(self, value):
        self._response = value.encode('UTF-8')


@pytest.fixture(scope='function', autouse=True)
def mock_telnet(monkeypatch):
    mock = MockConnectionFactory()
    mock.response = 'OK\r\n'  # standard response
    monkeypatch.setattr(telnetlib, 'Telnet', mock)
    return mock

@pytest.fixture(scope='function')
def jambel(mock_telnet):
    light = _jambel.Jambel('my.host')
    light.__connection = mock_telnet
    return light


def test_init_jambel(jambel):
    assert jambel.host == 'my.host'
    assert jambel.port == jambel.DEFAULT_PORT


def test_init_jambel_with_custom_port():
    jambel = _jambel.Jambel('my.host', 8000)
    assert jambel.host == 'my.host'
    assert jambel.port == 8000


def test_status(jambel):
    jambel.__connection.response = 'status=0,0,0,1\r\n'
    assert jambel.status() == {_jambel.GREEN: 0, _jambel.RED: 0, _jambel.YELLOW: 0}


def test_status_for_individual_lights(jambel):
    jambel.__connection.response = 'status=2,3,4,1\r\n'
    assert jambel._order == [_jambel.RED, _jambel.YELLOW, _jambel.GREEN]
    assert jambel.green.status() == 4
    assert jambel.yellow.status() == 3
    assert jambel.red.status() == 2


def test_set_blink_time(jambel):
    jambel.set_blink_time(_jambel.RED, 234, 567)
    assert jambel.__connection.last_cmd == 'blink_time=1,234,567\n'


def test_set_blink_time_for_individual_lights(jambel):
    jambel.__connection.response = 'status=2,3,4,1\r\n'
    jambel.green.blink_time(12, 34)
    jambel.yellow.blink_time(56, 78)
    jambel.red.blink_time(90, 12)
    assert jambel.__connection.history()[:3] == [
        'blink_time=1,90,12',
        'blink_time=2,56,78',
        'blink_time=3,12,34',
    ]


def test_set(jambel):
    jambel.set(_jambel.PANIC)
    assert jambel.__connection.last_cmd == 'set_all=3,3,3,0\n'


def test_init_jambel_modules_bottom_up():
    jambel = _jambel.Jambel('my.host', green=_jambel.BOTTOM)
    assert jambel._order == [_jambel.GREEN, _jambel.YELLOW, _jambel.RED]

def test_init_jambel_modules_top_down():
    jambel = _jambel.Jambel('my.host', green=_jambel.TOP)
    assert jambel._order == [_jambel.RED, _jambel.YELLOW, _jambel.GREEN]


def test_main_needs_parameters():
    pytest.raises(SystemExit, _jambel.main, [])


@pytest.mark.parametrize('input,output', [
    ('my.host', ('my.host', _jambel.Jambel.DEFAULT_PORT)),
    ('my.host:8118', ('my.host', 8118)),
])
def test_main_jambel_address(mock_telnet, input, output):
    _jambel.main([input, 'version'])
    assert mock_telnet.last_cmd.strip() == 'version'
    assert mock_telnet.last_addr == output


@pytest.mark.parametrize('input,output', [
    (['version'], 'version'),
    (['red=on'],      'set=1,on'),
    (['yellow=off'],  'set=2,off'),
    (['green=blink'], 'set=3,blink'),
    (['red=off', '--red-on-top'],             'set=3,off'),
    (['yellow=flash', '--red-on-top'],        'set=2,flash'),
    (['green=blink_inverse', '--red-on-top'], 'set=1,blink_invers'),
])
def test_main_commands(mock_telnet, input, output):
    _jambel.main(['my.host'] + input)
    assert mock_telnet.last_cmd.strip() == output


def test_main_multiple_commands_are_executed_in_order(mock_telnet):
    _jambel.main(['my.host', 'green=on', 'yellow=blink', 'red=off', '--debug'])
    assert mock_telnet.history() == ['set=1,off', 'set=2,blink', 'set=3,on']


