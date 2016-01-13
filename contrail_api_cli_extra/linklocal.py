# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError

from .utils import ip_type


class Linklocal(Command):
    description = "Provision linklocal services"
    oper = Arg(help='Add or remove linklocal service',
               choices=['add', 'del'])
    service_name = Arg('--service-name',
                       help='Linklocal service name',
                       required=True)
    service_ip = Arg('--service-ip',
                     help='Linklocal service IP',
                     type=ip_type,
                     required=True)
    service_port = Arg('--service-port',
                       help='Linklocal service port',
                       type=int,
                       required=True)
    fabric_dns_service_name = Arg('--fabric-dns-service-name',
                                  help='DNS service name in the fabric')
    fabric_service_ip = Arg('--fabric-service-ip',
                            help='Service IP in the fabric',
                            type=ip_type)
    fabric_service_port = Arg('--fabric-service-port',
                              help='Service port in the fabric',
                              type=int,
                              required=True)

    def __call__(self, oper=None, service_name=None, service_ip=None, service_port=None,
                 fabric_dns_service_name=None, fabric_service_ip=None, fabric_service_port=None):

        try:
            vrouter_config = Resource('global-vrouter-config',
                                      fq_name='default-global-system-config:default-global-vrouter-config',
                                      check_fq_name=True,
                                      fetch=True)
        except ValueError:
            global_config = Resource('global-system-config',
                                     fq_name='default-global-system-config',
                                     check_fq_name=True)
            vrouter_config = Resource('global-vrouter-config',
                                      fq_name='default-global-system-config:default-global-vrouter-config',
                                      parent_uuid=global_config.uuid,
                                      parent_type='global-system-config')
            vrouter_config.save()

        linklocal_entry = {
            'ip_fabric_DNS_service_name': fabric_dns_service_name,
            'ip_fabric_service_ip': [],
            'ip_fabric_service_port': fabric_service_port,
            'linklocal_services_ip': service_ip,
            'linklocal_services_port': service_port,
            'linklocal_services_name': service_name
        }
        if fabric_service_ip:
            linklocal_entry[ip_fabric_service_ip].append(fabric_service_ip)

        if oper == 'add':
            self.add_linklocal(vrouter_config, linklocal_entry)
        elif oper == 'del':
            self.del_linklocal(vrouter_config, linklocal_entry)

    def add_linklocal(self, vrouter_config, linklocal_entry):
        if 'linklocal_services' not in vrouter_config:
            vrouter_config['linklocal_services'] = {}
        if 'linklocal_service_entry' not in vrouter_config['linklocal_services']:
            vrouter_config['linklocal_services']['linklocal_service_entry'] = []

        if linklocal_entry not in vrouter_config['linklocal_services']['linklocal_service_entry']:
            vrouter_config['linklocal_services']['linklocal_service_entry'].append(linklocal_entry)
        else:
            raise CommandError('Linklocal service already present')
        vrouter_config.save()

    def del_linklocal(self, vrouter_config, linklocal_entry):
        if 'linklocal_services' not in vrouter_config:
            raise CommandError('Linklocal service not found')
        if 'linklocal_service_entry' not in vrouter_config['linklocal_services']:
            raise CommandError('Linklocal service not found')
        try:
            vrouter_config['linklocal_services']['linklocal_service_entry'].remove(linklocal_entry)
        except ValueError:
            raise CommandError('Linklocal service not found')
        vrouter_config.save()
