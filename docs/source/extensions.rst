.. _extensions:

Making your own Automate Extensions
===================================


Extension Development
---------------------

Automate extensions allow extending Automate functionalities by writing external libraries
that may consist of new Service, Sensor, Actuator, or Callable classes.

To start developing automate extensions, it is recommended to use
`cookiecutter <http://cookiecutter.readthedocs.org/>`_ template. This is how it works:

#. Install ``cookiecutter`` 1.0.0 or newer::

       pip install cookiecutter

#. Generate a Automate extension project::

       cookiecutter https://github.com/tuomas2/cookiecutter-automate-ext-template.git

Cookiecutter asks few questions and you have great basis for starting your template
development. There will be created Python files where you may add your new custom
Automate classes.

For your classes to be exported to the Automate, make sure that they are listed in
``extension_classes`` list in ``__init__.py`` of the extension module.


All installed Automate Extensions are available from Automate applications and are imported
to automate namespace.

.. tip::
       You can install your extension in *editable* mode by running ``pip install -e .``
       in your extension root directory.

.. tip::
       You can look at :ref:`automate-extensions` for examples.

