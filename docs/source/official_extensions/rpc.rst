.. _automate-rpc:

Remote Procedure Call Support for Automate
==========================================

Introduction
------------

This extension provides XmlRPC API for external applications. Exported API is by default defined by
:class:`automate.plugins.rpc.rpc.ExternalApi`.

Installation
------------

Install extras::

    pip install automate[rpc]

Class definitions
-----------------

.. autoclass:: automate.plugins.rpc.RpcService
   :members:

.. autoclass:: automate.plugins.rpc.rpc.ExternalApi
   :members:

