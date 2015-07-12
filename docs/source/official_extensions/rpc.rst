.. _automate-rpc:

Remote Procedure Call Support for Automate
==========================================

Github URL: http://github.com/tuomas2/automate-rpc

Introduction
------------

This extension provides XmlRPC API for external applications. Exported API is by default defined by
:class:`automate_rpc.rpc.ExternalApi`.

Installation
------------

Install from Pypi::

    pip install automate-rpc

Optionally, you could install also by cloning GIT repository and installing manually::

    git clone https://github.com/tuomas2/automate-rpc.git
    cd automate-rpc
    ./setup.py install

Class definitions
-----------------

.. autoclass:: automate_rpc.RpcService
   :members:

.. autoclass:: automate_rpc.rpc.ExternalApi
   :members:

