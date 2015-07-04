#!/usr/bin/env python

from setuptools import setup, find_packages
from pip.req import parse_requirements
import re


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']

install_reqs = parse_requirements('requirements.pip')
setupopts = dict(
    name="automate",
    version=get_version('automate/__init__.py'),
    packages=find_packages(),

    scripts=["automate_clean_app.py", 'generate_selfsigned_certificate.sh'],
    install_requires=[str(ir.req) for ir in install_reqs],

    package_data={},

    test_suite='py.test',
    test_require=['pytest', 'pytest-capturelog'],

    # metadata for upload to PyPI
    author="Tuomas Airaksinen",
    author_email="tuomas.airaksinen@gmail.com",
    description="Python library and application (with GUI) for simple formulation of advanced automation solutions.",
    long_description="Automate can be used to easily formulate advanced rules for automatization of several different "
                     "electrical equipments with different sensors and actuators (/actuator/ is "
                     "any physical equipment or software function that does something with "
                     "some conditions).",
    license="Free for non-commercial use",
    keywords="automation, GPIO, Raspberry Pi, RPIO, enaml, traits",
    url="http://github.com/tuomas2/automate",
    #    entry_points={'automate.service_extension': ['builtin_services = automate.services'],
    #                  'automate.sensor_extension': ['builtin_sensors = automate.sensors'],
    #                  'automate.actuator_extension': ['builtin_actuators = automate.actuators'],
    #                  'automate.logic_extension': ['builtin_logic = automate.logic']
    #                  },

    classifiers=["Development Status :: 4 - Beta",
                 "Environment :: Console",
                 "Environment :: X11 Applications :: Qt",
                 "Environment :: Win32 (MS Windows)",
                 "Environment :: Web Environment",
                 "Intended Audience :: Education",
                 "Intended Audience :: End Users/Desktop",
                 "Intended Audience :: Developers",
                 "Intended Audience :: Information Technology",
                 "License :: Free for non-commercial use",
                 "Operating System :: Microsoft :: Windows",
                 "Operating System :: POSIX",
                 "Programming Language :: Python :: 2.7",
                 "Topic :: Scientific/Engineering",
                 "Topic :: Software Development",
                 "Topic :: Software Development :: Libraries"]
)

if __name__ == "__main__":
    setup(**setupopts)
