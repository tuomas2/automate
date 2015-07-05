#!/usr/bin/env python

from setuptools import setup, find_packages

def get_version(filename):
    import re
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']

setupopts = dict(
    name="automate",
    version=get_version('automate/__init__.py'),
    packages=find_packages(),
    install_requires=[
        'traits==4.5.0',
        'croniter==0.3.8',
        'pyinotify==0.9.6',
        'ipython==3.2',
        'ansiconv==1.0',
        'colorlog==2.6'],
    test_suite='py.test',
    test_require=['pytest', 'pytest-capturelog'],
    author="Tuomas Airaksinen",
    author_email="tuomas.airaksinen@gmail.com",
    description="Automate is a general purpose Python automatization library.",
    long_description="Automate is a general purpose Python automatization library. Its objective is to offer "
                     "convenient and robust object-oriented programming framework for complex state machine systems. "
                     "Automate can be used to design complex automation systems, yet it is easy to learn and fun to use. "
                     "It was originally developed with home robotics/automatization projects in mind, but is quite general "
                     "in nature and could find applications from various fields. Automate can be embedded in other "
                     "Python software as a component, which runs its operation in its own threads.",
    license="GPL",
    keywords="automation, GPIO, Raspberry Pi, RPIO, traits",
    url="http://github.com/tuomas2/automate",

    classifiers=["Development Status :: 4 - Beta",
                 "Environment :: Console",
                 "Environment :: Web Environment",
                 "Intended Audience :: Education",
                 "Intended Audience :: End Users/Desktop",
                 "Intended Audience :: Developers",
                 "Intended Audience :: Information Technology",
                 "License :: OSI Approved :: GNU General Public License (GPL)",
                 "Operating System :: Microsoft :: Windows",
                 "Operating System :: POSIX",
                 "Programming Language :: Python :: 2.7",
                 "Topic :: Scientific/Engineering",
                 "Topic :: Software Development",
                 "Topic :: Software Development :: Libraries"]
)

if __name__ == "__main__":
    setup(**setupopts)
