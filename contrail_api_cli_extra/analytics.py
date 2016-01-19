# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import json

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource, Collection

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
        try:
            analytics = Resource('analytics-node',
                                 fq_name='default-global-system-config:%s' % analytics_name,
                                 fetch=True)
            analytics.delete()
        except ValueError as e:
            raise CommandError(text_type(e))


class ListAnalytics(Command):
    description = 'List analytics nodes'

    def __call__(self):
        analytics = Collection('analytics-node',
                               fetch=True, recursive=2)
        return json.dumps([{'analytics_name': analytic.fq_name[-1],
                            'analytics_ip': analytic['analytics_node_ip_address']}
                           for analytic in analytics], indent=2)
