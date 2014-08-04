
import itertools
import time

from jambel import OFF, ON, Jambel

WAIT = 1.5  # in seconds

PHASES = [
    (ON, OFF, OFF),
    (OFF, ON, OFF),
    (OFF, OFF, ON),
    (OFF, ON, ON)
]

light = Jambel('ampel3.dev.jambit.com')
for phase in itertools.cycle(PHASES):
    light.set(phase)
    time.sleep(WAIT)

