"""
This package contains contrail-api-cli commands to ease operating/fixing
a contrail installation.

Commands are grouped in different packages with different purposes:

* :py:mod:`contrail_api_cli_extra.clean`: commands to detect and remove bad resources
* :py:mod:`contrail_api_cli_extra.fix`: commands to detect and fix bad resources
* :py:mod:`contrail_api_cli_extra.migration`: commands to handle data migration
  when upgrading contrail to a new major version
* :py:mod:`contrail_api_cli_extra.misc`: general purpose commands
* :py:mod:`contrail_api_cli_extra.provision`: commands used to
  provision/configure a contrail installation

Installation
============

In the contrail-api-cli-extra directory run::

    python setup.py install

If all goes well you will see new commands in contrail-api-cli::

    contrail-api-cli --host 1.2.3.4 shell
    1.2.3.4:/> help
    Available commands: schema shell exec edit tree cat relative ln kv rm python du
    ls find-orphaned-projects fix-subnets fix-vn-id fix-fip-locks reschedule-vm fix-sg
    rpf provision dot exit help cd

"""
