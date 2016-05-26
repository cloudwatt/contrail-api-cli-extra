# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.exceptions import CommandError
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.utils import FQName

from ..utils import ip_type, port_type, md5_type, RouteTargetAction

ADDRESS_FAMILIES = ['route-target', 'inet-vpn', 'e-vpn', 'erm-vpn',
                    'inet6-vpn']
DEFAULT_RI_FQ_NAME = ['default-domain', 'default-project', 'ip-fabric',
                      '__default__']


class BGPRouter(Command):
    router_name = Arg(help="BGP router name")


class AddBGPRouter(BGPRouter):
    description = "Add BgpRouter to the API server"
    router_ip = Option(help="BGP router IP", type=ip_type)
    router_port = Option(help="BGP port (default: %(default)s)",
                         type=port_type, default=179)
    router_asn = Option(type=RouteTargetAction.asn_type, default=64512,
                        help="Autonomous System Number (default: %(default)s)")
    router_type = Option(default='contrail',
                         help="BGP router type ('contrail' for Contrail control \
                               nodes and '<WHATEVER>' for non Contrail BGP \
                               routers) (default: %(default)s)")
    router_address_families = Option(nargs='+',
                                     help="Address family list \
                                           (default: %(default)s)",
                                     choices=ADDRESS_FAMILIES,
                                     default=ADDRESS_FAMILIES)
    router_md5 = Option(default=None, type=md5_type,
                        help="MD5 authentication (default: %(default)s)")

    def __call__(self, router_name=None, router_ip=None, router_port=None,
                 router_asn=None, router_address_families=[],
                 router_type=None, router_md5=None):

        default_ri = Resource('routing-instance', fq_name=DEFAULT_RI_FQ_NAME,
                              check=True)
        router_fq_name = DEFAULT_RI_FQ_NAME + [router_name]

        bgp_router = Resource('bgp-router',
                              fq_name=router_fq_name)
        if bgp_router.exists:
            raise CommandError("The BGP router %s already exists" %
                               FQName(router_fq_name))

        if router_type != 'contrail' and 'erm-vpn' in router_address_families:
            router_address_families.remove('erm-vpn')

        auth_data = None
        if router_md5:
            auth_data = {
                'key_items': [{
                    'key': router_md5,
                    'key_id': 0,
                }],
                'key_type': 'md5',
            }
        router_parameters = {
            'address': router_ip,
            'address_families': {
                'family': router_address_families,
            },
            'autonomous_system': router_asn,
            'identifier': router_ip,
            'port': router_port,
            'vendor': router_type,
            'auth_data': auth_data,
        }

        # full-mesh with existing BGP routers
        bgp_router_refs = []
        for bgp_router_neighbor in Collection('bgp-router',
                                              parent_uuid=default_ri.uuid,
                                              fetch=True):
            bgp_router_refs.append({
                'to': bgp_router_neighbor.fq_name,
                'attr': {
                    'session': [{
                        'attributes': [{
                            'address_families': {
                                'family': router_address_families,
                            },
                            'auth_data': auth_data,
                        }],
                    }],
                },
            })

        bgp_router = Resource('bgp-router',
                              fq_name=router_fq_name,
                              parent=default_ri,
                              bgp_router_parameters=router_parameters,
                              bgp_router_refs=bgp_router_refs)
        bgp_router.save()


class DelBGPRouter(BGPRouter):
    description = "Delete BgpRouter to the API server"

    def __call__(self, router_name=None):
        router_fq_name = DEFAULT_RI_FQ_NAME + [router_name]
        bgp_router = Resource('bgp-router',
                              fq_name=router_fq_name,
                              check=True)
        bgp_router.delete()


class ListBGPRouter(Command):
    description = 'List bgp routers'

    def __call__(self):
        routers = Collection('bgp-router',
                             fetch=True, recursive=2)
        return json.dumps([{'router_name': router.fq_name[-1],
                            'router_ip': router['bgp_router_parameters']['address'],
                            'router_port': router['bgp_router_parameters']['port'],
                            'router_asn': router['bgp_router_parameters']['autonomous_system'],
                            'router_type': router['bgp_router_parameters']['vendor'],
                            'router_address_families': router['bgp_router_parameters']['address_families']['family'],
                            'router_md5': router['bgp_router_parameters']['auth_data']['key_items'][0]['key']
                                          if 'auth_data' in router['bgp_router_parameters']
                                          and router['bgp_router_parameters']['auth_data'] else []}
                          for router in routers], indent=2)
