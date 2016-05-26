# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.resource import Resource, Collection

from ..utils import ip_type


class Config(Command):
    config_name = Arg(help='Hostname of config node')


class AddConfig(Config):
    description = 'Add config node'
    config_ip = Option(help='IP of config node',
                       type=ip_type,
                       required=True)

    def __call__(self, config_name=None, config_ip=None):

        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config')
        config = Resource('config-node',
                          fq_name='default-global-system-config:%s' % config_name,
                          parent=global_config,
                          config_node_ip_address=config_ip)
        config.save()


class DelConfig(Config):
    description = 'Remove config node'

    def __call__(self, config_name=None):
        config = Resource('config-node',
                          fq_name='default-global-system-config:%s' % config_name,
                          check=True)
        config.delete()


class ListConfig(Command):
    description = 'List config nodes'

    def __call__(self):
        configs = Collection('config-node',
                             fetch=True, recursive=2)
        return json.dumps([{'config_name': config.fq_name[-1],
                            'config_ip': config['config_node_ip_address']}
                           for config in configs], indent=2)
