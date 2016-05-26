# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Option
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError, ResourceNotFound

from ..utils import ip_type


class Linklocal(Command):
    service_name = Option(help='Linklocal service name',
                          required=True)
    service_ip = Option(help='Linklocal service IP',
                        type=ip_type,
                        required=True)
    service_port = Option(help='Linklocal service port',
                          type=int,
                          required=True)
    fabric_dns_service_name = Option(help='DNS service name in the fabric')
    fabric_service_ip = Option(help='Service IP in the fabric',
                               type=ip_type)
    fabric_service_port = Option(help='Service port in the fabric',
                                 type=int,
                                 required=True)

    def __call__(self, service_name=None, service_ip=None, service_port=None,
                 fabric_dns_service_name=None, fabric_service_ip=None, fabric_service_port=None):

        if not fabric_dns_service_name and not fabric_service_ip:
            raise CommandError('--fabric_dns_service_name or --fabric_service_ip required')

        self.linklocal_entry = {
            'ip_fabric_DNS_service_name': fabric_dns_service_name,
            'ip_fabric_service_ip': [],
            'ip_fabric_service_port': fabric_service_port,
            'linklocal_service_ip': service_ip,
            'linklocal_service_port': service_port,
            'linklocal_service_name': service_name
        }
        if fabric_service_ip:
            self.linklocal_entry['ip_fabric_service_ip'].append(fabric_service_ip)

        try:
            self.vrouter_config = Resource('global-vrouter-config',
                                           fq_name='default-global-system-config:default-global-vrouter-config',
                                           fetch=True)
        except ResourceNotFound:
            global_config = Resource('global-system-config',
                                     fq_name='default-global-system-config')
            self.vrouter_config = Resource('global-vrouter-config',
                                           fq_name='default-global-system-config:default-global-vrouter-config',
                                           parent=global_config)
            self.vrouter_config.save()


class AddLinklocal(Linklocal):
    description = 'Add linklocal service'

    def __call__(self, service_name=None, service_ip=None, service_port=None,
                 fabric_dns_service_name=None, fabric_service_ip=None, fabric_service_port=None):
        super(AddLinklocal, self).__call__(service_name, service_ip, service_port,
                                           fabric_dns_service_name, fabric_service_ip, fabric_service_port)

        if 'linklocal_services' not in self.vrouter_config:
            self.vrouter_config['linklocal_services'] = {}
        if 'linklocal_service_entry' not in self.vrouter_config['linklocal_services']:
            self.vrouter_config['linklocal_services']['linklocal_service_entry'] = []

        if self.linklocal_entry not in self.vrouter_config['linklocal_services']['linklocal_service_entry']:
            self.vrouter_config['linklocal_services']['linklocal_service_entry'].append(self.linklocal_entry)
        else:
            raise CommandError('Linklocal service already present')
        self.vrouter_config.save()


class DelLinklocal(Linklocal):
    description = 'Remove linklocal service'

    def __call__(self, service_name=None, service_ip=None, service_port=None,
                 fabric_dns_service_name=None, fabric_service_ip=None, fabric_service_port=None):
        super(DelLinklocal, self).__call__(service_name, service_ip, service_port,
                                           fabric_dns_service_name, fabric_service_ip, fabric_service_port)

        if 'linklocal_services' not in self.vrouter_config:
            raise CommandError('Linklocal service not found')
        if 'linklocal_service_entry' not in self.vrouter_config['linklocal_services']:
            raise CommandError('Linklocal service not found')
        try:
            self.vrouter_config['linklocal_services']['linklocal_service_entry'].remove(self.linklocal_entry)
        except ValueError:
            raise CommandError('Linklocal service not found')
        self.vrouter_config.save()


class ListLinklocal(Command):
    description = 'List linklocal services'

    def __call__(self):
        try:
            vrouter_config = Resource('global-vrouter-config',
                                      fq_name='default-global-system-config:default-global-vrouter-config',
                                      fetch=True)
            if 'linklocal_services' in vrouter_config:
                return json.dumps([{'service_name': service['linklocal_service_name'],
                                    'service_ip': service['linklocal_service_ip'],
                                    'service_port': service['linklocal_service_port'],
                                    'fabric_dns_service_name': service.get('ip_fabric_DNS_service_name'),
                                    'fabric_service_ip': service['ip_fabric_service_ip'],
                                    'fabric_service_port': service['ip_fabric_service_port']}
                                  for service in vrouter_config['linklocal_services'].get('linklocal_service_entry', [])], indent=2)
        except ResourceNotFound:
            pass
        return json.dumps([])
