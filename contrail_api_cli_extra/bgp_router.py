# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.exceptions import CommandError
from contrail_api_cli.resource import Resource
from contrail_api_cli.utils import FQName

from .utils import ip_type, port_type, RouteTargetAction

ADDRESS_FAMILIES = ['route-target', 'inet-vpn', 'e-vpn', 'erm-vpn',
                    'inet6-vpn']
DEFAULT_RI_FQ_NAME = ['default-domain', 'default-project', 'ip-fabric',
                      '__default__']


class AddBGPRouter(Command):
    description = "Add BgpRouter to the API server"
    router_name = Arg(help="BGP router name")
    router_ip = Arg('--router-ip', help="BGP router IP", type=ip_type)
    router_port = Arg('--router-port', help="BGP port (default: %(default)s)",
                      type=port_type, default=179)
    router_asn = Arg('--router-asn', type=RouteTargetAction.asn_type, default=64512,
                     help="Autonomous System Number (default: %(default)s)")
    router_type = Arg('--router-type', default='contrail',
                      help="BGP router type ('contrail' for Contrail control \
                            nodes and '<WHATEVER>' for non Contrail BGP \
                            routers) (default: %(default)s)")
    router_address_families = Arg('--router-address-families', nargs='+',
                                  help="Address family list \
                                        (default: %(default)s)",
                                  choices=ADDRESS_FAMILIES,
                                  default=ADDRESS_FAMILIES)

    def __call__(self, router_name=None, router_ip=None, router_port=None,
                 router_asn=None, router_address_families=[],
                 router_type=None):

        default_ri = Resource('routing-instance', fq_name=DEFAULT_RI_FQ_NAME,
                              check_fq_name=True)
        router_fq_name = DEFAULT_RI_FQ_NAME + [router_name]

        try:
            bgp_router = Resource('bgp-router',
                                  fq_name=router_fq_name,
                                  check_fq_name=True)
            raise CommandError("The BGP router %s already exists" %
                               FQName(router_fq_name))
        except ValueError:
            pass

        if router_type != 'contrail' and 'erm-vpn' in router_address_families:
            router_address_families.remove('erm-vpn')
        router_parameters = {
            'address': router_ip,
            'address_families': {
                'family': router_address_families
            },
            'autonomous_system': router_asn,
            'identifier': router_ip,
            'port': router_port,
            'vendor': router_type
        }
        bgp_router = Resource('bgp-router',
                              fq_name=router_fq_name)
        bgp_router['parent_type'] = 'routing-instance'
        bgp_router['parent_uuid'] = default_ri.uuid
        bgp_router['bgp_router_parameters'] = router_parameters
        bgp_router.save()


class DelBGPRouter(Command):
    description = "Delete BgpRouter to the API server"
    router_name = Arg(help="BGP router name")

    def __call__(self, router_name=None):
        try:
            router_fq_name = DEFAULT_RI_FQ_NAME + [router_name]
            bgp_router = Resource('bgp-router',
                                  fq_name=router_fq_name,
                                  check_fq_name=True)
        except ValueError:
            raise CommandError("BGP router %s doesn't exists" %
                               FQName(router_fq_name))
        bgp_router.delete()
