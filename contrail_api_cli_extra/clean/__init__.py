"""
Module containing commands to clean bad resources.

Since these commands are sensitive as they will probably remove resources
the ``contrail_api_cli.clean`` namespace must be loaded explicitely to
be able to run the commands::

    contrail-api-cli --ns contrail_api_cli.clean <command>
"""
