# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.client import HttpError
from contrail_api_cli.resource import Resource
from contrail_api_cli.utils import printo, parallel_map
from contrail_api_cli.command import Arg
from contrail_api_cli.context import Context

from ..utils import CheckCommand


class FixSubnets(CheckCommand):
    """Fix subnet/vn association in kv store.

    When the API server is not properly started the hooks that populates
    the kv store on subnet creation are not properly run. As a result
    doing neutron net-list will lead to the following error::

        404-{u'NeutronError': {u'message': u'Subnet 646f986a-67c9-4e1b-bf13-59f18f787068 could not be found', u'type': u'SubnetNotFound', u'detail': u''}}

    This command check all the IPAM subnet informations and verifies that
    proper kv store keys exists for each subnet.

    This command assumes there is only one IPAM in the contrail installation
    (``default-domain:default-project:default-network-ipam``).

    To check all subnets run::

        contrail-api-cli fix-subnets --check

    To fix all subnets run::

        contrail-api-cli fix-subnets [--dry-run]

    Or to fix a particular subnet run::

        contrail-api-cli fix-subnets <subnet_uuid> [--dry-run]
    """
    description = "Fix subnets key-value store entries"
    subnet_uuid = Arg(nargs="?", help="subnet uuid to fix")

    def _subnet_key(self, vn_uuid, subnet):
        return "%s %s/%s" % (vn_uuid,
                             subnet['subnet']['ip_prefix'],
                             subnet['subnet']['ip_prefix_len'])

    def chk(self, item):
        vn_uuid, subnet_uuid, subnet = item
        to_add = []
        if self.subnet_uuid is not None and self.subnet_uuid != subnet_uuid:
            return to_add
        subnet_key = self._subnet_key(vn_uuid, subnet)
        try:
            self.session.search_kv_store(subnet_uuid)
        except HttpError:
            printo('Missing key %s for subnet %s' % (subnet_uuid, subnet_uuid))
            to_add.append((subnet_uuid, subnet_key))
        try:
            self.session.search_kv_store(subnet_key)
        except HttpError:
            printo('Missing key %s for subnet %s' % (subnet_key, subnet_uuid))
            to_add.append((subnet_key, subnet_uuid))
        return to_add

    def fix(self, to_add):
        for (key, value) in to_add:
            printo('Adding kv %s:%s' % (key, value))
            if not self.dry_run:
                self.session.add_kv_store(key, value)

    def __call__(self, subnet_uuid=None, **kwargs):
        super(FixSubnets, self).__call__(**kwargs)

        self.session = Context().session
        self.subnet_uuid = subnet_uuid

        ipam = Resource('network-ipam',
                        fq_name='default-domain:default-project:default-network-ipam',
                        fetch=True)

        to_check = [(vn.uuid, subnet.get('subnet_uuid'), subnet)
                    for vn in ipam.back_refs.virtual_network
                    for subnet in vn.get('attr', {}).get('ipam_subnets', [])]
        to_fix = parallel_map(self.chk, to_check, workers=50)
        if not self.dry_run and not self.check:
            parallel_map(self.fix, to_fix, workers=50)
