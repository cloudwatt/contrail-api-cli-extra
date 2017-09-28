# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.context import Context
from contrail_api_cli.resource import Resource
from contrail_api_cli.utils import printo, continue_prompt

from ..utils import CheckCommand


class CleanSubnet(CheckCommand):
    """Command to fix subnets KV store.

    This command works by first retrieving all the KV store, then it
    builds a dict which tends to reproduce a clean KV store based on
    the virtual-network back-refs objects present in the API. Finally
    it compares the clean KV store with the current one and retrieves
    the keys of the stale entries to remove it in the current KV store.

    To run the command::

        contrail-api-cli --ns contrail_api_cli.clean clean-subnet
    """

    description = "Clean stale contrail ipam-subnets"

    def _get_kv_store(self, session):
        return session.get_kv_store()

    def _get_vn_back_refs(self):
        return Resource(
            'network-ipam',
            fq_name='default-domain:default-project:default-network-ipam',
            fetch=True)['virtual_network_back_refs']

    def _get_healthy_kv(self, vn_back_refs):
        """Build a dict which reproduces a healthy KV store

        For each vn it will two key-pair entries. Example:
        kv = {
              "6c725bae-a5d6-4a29-bea7-c24b4ed3dc2b 10.1.0.0/24" : "6f620bf3-ca0c-4331-8dcf-bbf3a93fa3d7"
              "062d7842-07eb-429d-9002-d404dc773939 10.2.0.0/24" : "062d7842-07eb-429d-9002-d404dc773939"
             }
        """
        kv = {}

        for vn in vn_back_refs:
            if not vn['attr']['ipam_subnets']:
                continue
            for subnet in vn['attr']['ipam_subnets']:
                vn_uuid = str("%s %s/%s" % (vn['uuid'],
                                            subnet['subnet']['ip_prefix'],
                                            subnet['subnet']['ip_prefix_len']))
                subnet_uuid = str(subnet['subnet_uuid'])

                kv.update({subnet_uuid: vn_uuid})
                kv.update({vn_uuid: subnet_uuid})
        printo("Clean KV store should have %d entries." % len(kv))
        return kv

    def _get_stale_subnets(self, kv, healthy_kv):
        stale_subnets = []
        for _dict in kv:
            key = _dict['key']
            value = _dict['value']
            if not (key in healthy_kv and str(value) == healthy_kv[key]):
                stale_subnets.append(key)
        printo("Current KV store contains %d stale entries." %
               len(stale_subnets))
        return stale_subnets

    def _clean_kv(self, session, stale_subnets, dry_run=False):
        if continue_prompt("Do you really want to delete these entries ?"):
            for key in stale_subnets:
                if not dry_run:
                    session.remove_kv_store(key)
                printo(
                    "Entry with key \"%s\" has been removed from the KV store" %
                    key)

    def __call__(self, **kwargs):
        super(CleanSubnet, self).__call__(**kwargs)
        session = Context().session
        vn_back_refs = self._get_vn_back_refs()
        kv = self._get_kv_store(session)

        healthy_kv = self._get_healthy_kv(vn_back_refs)
        stale_subnets = self._get_stale_subnets(kv, healthy_kv)

        if self.check:
            return

        self._clean_kv(session, stale_subnets, self.dry_run)
        return "Clean stale subnets ended"
