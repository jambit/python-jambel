
import telnetlib
import pytest

from jambel import Jambel, PANIC


class TelnetMock(object):

    def __init__(self, host, port):
        self.host, self.port = host, port
        self.closed = False
        self._last_cmd = None
        self.mock_response = None

    def write(self, cmd):
        self._last_cmd = cmd

    def read_until(self, *args, **kwargs):
        return self.mock_response

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def mock_telnet(monkeypatch):
    monkeypatch.setattr(telnetlib, 'Telnet', TelnetMock)

@pytest.fixture(scope='function')
def jambel(request):
    return Jambel('my.host')


def test_init_jambel(jambel):
    assert jambel._conn.host == 'my.host'
    assert jambel._conn.port == Jambel.DEFAULT_PORT


def test_init_jambel_with_custom_port():
    jambel = Jambel('my.host', 8000)
    assert jambel._conn.host == 'my.host'
    assert jambel._conn.port == 8000


def test_status(jambel):
    jambel._conn.mock_response = 'status=0,0,0,1\r\n'
    assert jambel.status() == [0, 0, 0]


def test_set(jambel):
    jambel.set(PANIC)
    assert jambel._conn._last_cmd == 'set_all=3,3,3,0\n'
