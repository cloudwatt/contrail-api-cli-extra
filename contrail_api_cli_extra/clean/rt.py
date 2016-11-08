# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six import text_type

from contrail_api_cli.utils import printo, parallel_map
from contrail_api_cli.exceptions import ResourceNotFound
from contrail_api_cli.command import Option

from ..utils import CheckCommand, ZKCommand, PathCommand


class CleanRT(CheckCommand, ZKCommand, PathCommand):
    """Removes stale route-targets.

    RTs that are not linked to a logical-router or a routing-instance are
    considered as staled and will be removed. If a ZK lock exists for the
    RT it will be removed::

        contrail-api-cli --ns contrail_api_cli.clean clean-route-target --zk-server <ip> [route-target/uuid]

    If no route-target path is provided all RTs are considered. ``--check`` and ``--dry-run``
    options are available.

    You can exclude RT from the cleaning process::

        contrail-api-cli --ns contrail_api_cli.clean clean-route-target --exclude <RT_FQNAME> --exclude <RT_FQNAME> [...]
    """

    exclude = Option('-e', action="append", default=[],
                     help="Exclude RT from the clean procedure")
    description = "Clean stale route targets"

    @property
    def resource_type(self):
        return "route-target"

    def log(self, message, rt):
        printo('[%s] %s' % (rt.uuid, message))

    def _get_rt_id(self, rt):
        return int(rt['name'].split(':')[-1])

    def _get_zk_node(self, rt_id):
        return '/id/bgp/route-targets/%010d' % rt_id

    def _ensure_lock(self, rt):
        rt_id = self._get_rt_id(rt)
        # No locks created for rt_id < 8000000
        if rt_id < 8000000:
            return
        zk_node = '/id/bgp/route-targets/%010d' % rt_id
        if not self.zk_client.exists(zk_node):
            if rt.get('logical_router_back_refs'):
                fq_name = rt['logical_router_back_refs'][0].fq_name
            else:
                # FIXME: can't determine routing-instance for route-target
                # don't create any lock
                return
            if not self.dry_run:
                self.zk_client.create(zk_node, text_type(fq_name).encode('utf-8'))
            self.log("Added missing ZK lock %s" % zk_node, rt)

    def _clean_rt(self, rt):
        try:
            if not self.dry_run:
                rt.delete()
            self.log("Removed RT %s" % rt.path, rt)
            rt_id = self._get_rt_id(rt)
            zk_node = self._get_zk_node(rt_id)
            if self.zk_client.exists(zk_node):
                if not self.dry_run:
                    self.zk_client.delete(zk_node)
                self.log("Removed ZK lock %s" % zk_node, rt)
        except ResourceNotFound:
            pass

    def _check_rt(self, rt):
        try:
            rt.fetch()
        except ResourceNotFound:
            return
        if not rt.get('routing_instance_back_refs') and not rt.get('logical_router_back_refs'):
            if text_type(rt.fq_name) in self.exclude:
                self.log('RT %s staled [excluded]' % rt.fq_name, rt)
            else:
                self.log('RT %s staled' % rt.fq_name, rt)
                if self.check is not True:
                    self._clean_rt(rt)
        else:
            self._ensure_lock(rt)

    def __call__(self, exclude=None, **kwargs):
        super(CleanRT, self).__call__(**kwargs)
        self.exclude = exclude
        parallel_map(self._check_rt, self.resources, workers=50)
