from setuptools import setup
import os
import re


def get_version():
    """
    Extracts version directly from Jambel module.
    """
    version_reg = re.compile("""^__version__ = '(.*)'""", re.M)
    _here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(_here, 'jambel.py')
    m = version_reg.search(open(path).read())
    return m.group(1) if m is not None else '?'


setup(
    name='jambel',
    version=get_version(),
    py_modules=['jambel'],
    url='http://github.com/jambit/python-jambel',
    license='MIT',
    author='Sebastian Rahlf',
    author_email='sebastian.rahlf@jambit.com',
    description="Interface to jambit's fast feedback lights.",
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    extras_require={
        # https://stackoverflow.com/a/32513360/294082
        'testing': [
            'pytest',
            'pytest-cov',
            'pyserial',
        ]
    },
    entry_points={
        'console_scripts': [
            'jambel = jambel:main',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
