#!/usr/bin/env python

from setuptools import setup, find_packages

setupopts = dict(
    name="automate",
    version='0.10.1',
    packages=find_packages('src'),
    include_package_data=True,
    package_dir={'': 'src'},
    zip_safe=False,
    install_requires=[
        "ansiconv",
        "colorlog",
        "croniter~=0.3",
        "future",
        "ipython<6.0",
        "pyinotify",
        "traits~=4.6",
        ],
    extras_require={
        'web':
            [
                "Django~=1.9",
                "django-crispy-forms~=1.6",
                "tornado~=4.5",
            ],
        'rpc': ['tornado~=4.5'],
        'raspberrypi': ['RPIO'],
        'arduino': ['pyfirmata'],
    },

    download_url='https://pypi.python.org/pypi/automate',
    platforms = ['any'],
    author="Tuomas Airaksinen",
    author_email="tuomas.airaksinen@gmail.com",
    description="General purpose Python automatization library with nifty real-time web UI",
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
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.6",
                 "Topic :: Scientific/Engineering",
                 "Topic :: Software Development",
                 "Topic :: Software Development :: Libraries",
                 "Topic :: Software Development :: Libraries :: Application Frameworks",
                 ],
    entry_points={'automate.extension': [
        'arduino = automate.extensions.arduino:extension_classes',
        'rpc = automate.extensions.rpc:extension_classes',
        'rpio = automate.extensions.rpio:extension_classes',
        'webui = automate.extensions.webui:extension_classes',
    ]
},

)

if __name__ == "__main__":
    setup(**setupopts)
