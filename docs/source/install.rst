How to Install Automate?
========================

Automate can be installed like ordinary python package. I highly recommend using virtualenv because
automate involves some strict version requirements for the libraries it uses.

(optional): Create and start using virtualenv::

    mkvirtualenv automate
    workon automate


Install from pypi::

    pip install automate

If you want to install some extensions too, you may also run::

    pip install automate-webui
    pip install automate-rpc
    pip install automate-arduino
    pip install automate-rpio

Install from git repository::

    ./setup.py install


