# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type

from keystoneclient.exceptions import HttpError

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError

from .utils import ip_type


class Config(Command):
    config_name = Arg(help='Hostname of config node')


class AddConfig(Config):
    description = 'Add config node'
    config_ip = Arg('--config-ip',
                     help='IP of config node',
                     type=ip_type,
                     required=True)

    def __call__(self, config_name=None, config_ip=None):

        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config',
                                 check_fq_name=True)
        config = Resource('config-node',
                          fq_name='default-global-system-config:%s' % config_name,
                          parent_type='global-system-config',
                          parent_uuid=global_config.uuid,
                          config_node_ip_address=config_ip)
        try:
            config.save()
        except HttpError as e:
            raise CommandError(text_type(e))


class DelConfig(Config):
    description = 'Remove config node'

    def __call__(self, config_name=None):
        try:
            config = Resource('config-node',
                              fq_name='default-global-system-config:%s' % config_name,
                              check_fq_name=True)
        except ValueError as e:
            raise CommandError(text_type(e))
        config.delete()
