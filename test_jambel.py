
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
        self._lastcmd = None
        self._response = None

    def __call__(self, host, port):
        return TelnetMock(self)

    @property
    def last_cmd(self):
        return self._lastcmd.decode('UTF-8')
    @last_cmd.setter
    def last_cmd(self, value):
        self._lastcmd = value

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
    assert jambel.status() == [0, 0, 0]


def test_set(jambel):
    jambel.set(_jambel.PANIC)
    assert jambel.__connection.last_cmd == 'set_all=3,3,3,0\n'


def test_init_jambel_modules_bottom_up():
    jambel = _jambel.Jambel('my.host', green=_jambel.BOTTOM)
    assert jambel.green._no == 1

def test_init_jambel_modules_top_down():
    jambel = _jambel.Jambel('my.host', green=_jambel.TOP)
    assert jambel.green._no == 3

