"""
A set of commands to provision/bootstrap a contrail environment.

Each command can be used separately but the more general case is to use the ``provision`` command
that will call appropriate commands given an environment specification file.

See :py:mod:`contrail_api_cli_extra.provision.provision`

Only the `provision` command is available in the default namespace. If you wish
to use other commands from the provision module use::

    contrail-api-cli --ns contrail_api_cli.provision list-bgp-router
"""
