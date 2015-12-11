#!/usr/bin/env python

from setuptools import setup, find_packages

def get_version(filename):
    import re
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']

setupopts = dict(
    name="automate",
    version=get_version('src/automate/__init__.py'),
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'traits>=4.6.0.dev354,<4.7.0',
        'croniter==0.3.8',
        'pyinotify==0.9.6',
        'ipython==4.0',
        'ansiconv==1.0',
        'colorlog==2.6',
        'future>=0.15.2',
        ],
    test_suite='py.test',
    tests_require=['pytest', 'pytest-capturelog'],
    download_url='https://pypi.python.org/pypi/automate',
    platforms = ['any'],
    author="Tuomas Airaksinen",
    author_email="tuomas.airaksinen@gmail.com",
    description="General purpose Python automatization library",
    long_description=open('README.rst').read(),
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
                 "Operating System :: POSIX :: Linux",
                 "Programming Language :: Python :: 2.7",
                 "Programming Language :: Python :: 3",
                 "Topic :: Scientific/Engineering",
                 "Topic :: Software Development",
                 "Topic :: Software Development :: Libraries",
                 "Topic :: Software Development :: Libraries :: Application Frameworks",
                 ]
)

if __name__ == "__main__":
    setup(**setupopts)
