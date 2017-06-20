How to Install Automate?
========================

Automate can be installed like ordinary python package. I recommend installation
in within virtual environment (see `virtualenv <https://virtualenv.pypa.io/en/latest/>`_).

#. (optional): Create and start using virtualenv::

    mkvirtualenv automate
    workon automate


#. Install from pypi::

    pip install automate

Optionally, you can specify some of the extras, i.e. web, rpc, raspberrypi, arduino::

   pip install automate[web,rpc,raspberrypi,arduino]

