How to Install Automate?
========================

Automate can be installed like ordinary python package. I recommend installation
in within virtual environment (see `virtualenv <https://virtualenv.pypa.io/en/latest/>`_).

#. (optional): Create and start using virtualenv::

    mkvirtualenv automate
    workon automate


#. Install from pypi::

    pip install automate

#. If you want to install some extensions too, you may also run::

    pip install automate-webui
    pip install automate-rpc
    pip install automate-arduino
    pip install automate-rpio

.. note:: Many examples in this documentation assume that extensions are installed!

Optionally, you could install also by cloning GIT repository and installing manually::

    git clone https://github.com/tuomas2/automate.git
    cd automate
    ./setup.py install

