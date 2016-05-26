# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.resource import Resource, Collection

from ..utils import ip_type


class Analytics(Command):
    analytics_name = Arg(help='Hostname of analytics node')


class AddAnalytics(Analytics):
    description = 'Add analytics node'
    analytics_ip = Option(help='IP of compute node',
                          type=ip_type,
                          required=True)

    def __call__(self, analytics_name=None, analytics_ip=None):
        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config')
        analytics = Resource('analytics-node',
                             fq_name='default-global-system-config:%s' % analytics_name,
                             parent=global_config,
                             analytics_node_ip_address=analytics_ip)

        analytics.save()


class DelAnalytics(Analytics):
    description = 'Remove analytics node'

    def __call__(self, analytics_name=None):
        analytics = Resource('analytics-node',
                             fq_name='default-global-system-config:%s' % analytics_name,
                             fetch=True)
        analytics.delete()


class ListAnalytics(Command):
    description = 'List analytics nodes'

    def __call__(self):
        analytics = Collection('analytics-node',
                               fetch=True, recursive=2)
        return json.dumps([{'analytics_name': analytic.fq_name[-1],
                            'analytics_ip': analytic['analytics_node_ip_address']}
                           for analytic in analytics], indent=2)
