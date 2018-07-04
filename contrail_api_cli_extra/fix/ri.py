# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six import text_type

from contrail_api_cli.utils import printo, FQName
from contrail_api_cli.exceptions import ResourceNotFound
from contrail_api_cli.resource import Resource

from ..utils import CheckCommand, ZKCommand, PathCommand


class FixRI(CheckCommand, ZKCommand, PathCommand):
    """Fix routing-instances without route-targets

        contrail-api-cli fix-ri --zk-server <ip> [routing-instance/uuid]

    """

    description = "Fix routing instances without route target"

    @property
    def resource_type(self):
        return "routing-instance"

    def log(self, message, ri):
        printo('[%s] %s' % (ri.uuid, message))

    def _refresh_rt_ids(self):
        self._rt_ids = sorted(map(int, self.zk_client.get_children('/id/bgp/route-targets')))

    def _add_rt_id(self, rt_id):
        self._rt_ids.append(rt_id)
        self._rt_ids.sort()

    def _get_free_rt_id(self):
        rt_id = self._rt_ids[-1] + 1
        if self.zk_client.exists('/id/bgp/route-targets/%010d' % rt_id):
            self._refresh_rt_ids()
            return self._get_free_rt_id()
        return rt_id

    def _lock_rt_id(self):
        rt_id = self._get_free_rt_id()
        fq_name = 'target:%d:%d' % (self.asn, rt_id)
        self.zk_client.create('/id/bgp/route-targets/%010d' % rt_id, text_type(fq_name).encode('utf-8'))
        self._add_rt_id(rt_id)
        return fq_name

    def _fix_ri(self, ri):
        if not self.dry_run:
            fq_name = self._lock_rt_id()
            rt = Resource('route-target', fq_name=[fq_name])
            rt.save()
            ri.add_ref(rt, attr={'import_export': None})
            self.log("Added RT %s (%s) to RI %s" % (rt.path, rt.fq_name, ri.path), ri)

    def _check_ri(self, ri):
        if ri.fq_name in [FQName('default-domain:default-project:__link_local__:__link_local__'),
                          FQName('default-domain:default-project:ip-fabric:__default__')]:
            return
        try:
            ri.fetch()
        except ResourceNotFound:
            return
        if len(ri.refs.route_target) == 0:
            self.log('RI %s has no RT' % ri.fq_name, ri)
            if not self.check:
                self._fix_ri(ri)

    def __call__(self, exclude=None, **kwargs):
        super(FixRI, self).__call__(**kwargs)
        self.asn = Resource('global-system-config',
                            fq_name='default-global-system-config',
                            fetch=True)['autonomous_system']
        self._refresh_rt_ids()
        for ri in self.resources:
            self._check_ri(ri)
