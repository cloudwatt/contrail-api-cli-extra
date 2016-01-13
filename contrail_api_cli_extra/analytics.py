# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource

from .utils import ip_type


class Analytics(Command):
    analytics_name = Arg(help='Hostname of analytics node')


class AddAnalytics(Analytics):
    description = 'Add analytics node'
    analytics_ip = Arg('--analytics-ip',
                       help='IP of compute node',
                       type=ip_type,
                       required=True)

    def __call__(self, analytics_name=None, analytics_ip=None):
        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config',
                                 check_fq_name=True)
        analytics = Resource('analytics-node',
                             fq_name='default-global-system-config:%s' % analytics_name,
                             parent_type='global-system-config',
                             parent_uuid=global_config.uuid,
                             analytics_node_ip_address=analytics_ip)

        analytics.save()


class DelAnalytics(Analytics):
    description = 'Remove analytics node'

    def __call__(self, analytics_name=None):
        analytics = Resource('analytics-node',
                             fq_name='default-global-system-config:%s' % analytics_name)
        analytics.delete()
