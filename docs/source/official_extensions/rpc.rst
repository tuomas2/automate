.. _automate-rpc:

Remote Procedure Call Support for Automate
==========================================

Introduction
------------

This extension provides XmlRPC API for external applications. Exported API is by default defined by
:class:`automate_rpc.rpc.ExternalApi`.

Installation
------------

Install extras::

    pip install automate[rpc]

Class definitions
-----------------

.. autoclass:: automate_rpc.RpcService
   :members:

.. autoclass:: automate_rpc.rpc.ExternalApi
   :members:

