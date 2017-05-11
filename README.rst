
python-jambel
=============

.. image:: https://travis-ci.org/jambit/python-jambel.svg?branch=master
    :target: https://travis-ci.org/jambit/python-jambel

Interface to jambit's project traffic lights.

A simple example::

    import jambel
    light = jambel.Jambel('ampel3.dev.jambit.com')
    light.green.on()
    light.yellow.blink()
    light.red.flash()

It is also possible to query the jambel's status::

    status = light.status()
    if stats[jambel.GREEN] == jambel.BLINK:
        print('green light is blinking!')

Interested in the hardware? Contact us at fast-feedback-lights@jambit.com
