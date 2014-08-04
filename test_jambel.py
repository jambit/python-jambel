
import telnetlib
import pytest

import jambel as _jambel


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
    return _jambel.Jambel('my.host')


def test_init_jambel(jambel):
    assert jambel._conn.host == 'my.host'
    assert jambel._conn.port == jambel.DEFAULT_PORT


def test_init_jambel_with_custom_port():
    jambel = _jambel.Jambel('my.host', 8000)
    assert jambel._conn.host == 'my.host'
    assert jambel._conn.port == 8000


def test_status(jambel):
    jambel._conn.mock_response = 'status=0,0,0,1\r\n'
    assert jambel.status() == [0, 0, 0]


def test_set(jambel):
    jambel.set(_jambel.PANIC)
    assert jambel._conn._last_cmd == 'set_all=3,3,3,0\n'


def test_init_jambel_modules_bottom_up():
    jambel = _jambel.Jambel('my.host', green=_jambel.BOTTOM)
    assert jambel.green._no == 1

def test_init_jambel_modules_top_down():
    jambel = _jambel.Jambel('my.host', green=_jambel.TOP)
    assert jambel.green._no == 3

