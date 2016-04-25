# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.command import Command, Arg, expand_paths
from contrail_api_cli.resource import Collection
from contrail_api_cli.utils import printo


class CleanStaleLBaasSI(Command):
    description = "Clean stale lbaas SIs"
    check = Arg('--check', '-c',
                default=False,
                action="store_true",
                help='Just check for stale LBaas SIs')
    dry_run = Arg('--dry-run', '-n',
                  default=False,
                  action="store_true",
                  help='Run this command in dry-run mode')
    paths = Arg(nargs="*", help="LBaas SI path(s)",
                metavar='path')

    def _is_stale(self, si):
        """Return True is the SI is stale.
        """

        if 'loadbalancer_pool_back_refs' not in si:
            printo('No pool attached to SI')
            return True

        pool = si['loadbalancer_pool_back_refs'][0]
        pool.fetch()

        if 'virtual_ip_back_refs' not in pool:
            printo('No VIP attached to pool')
            return True

        vip = pool['virtual_ip_back_refs'][0]
        vip.fetch()

        if 'virtual_machine_interface_refs' not in vip:
            printo('No VMI for VIP')
            return True

        vip_vmi = vip['virtual_machine_interface_refs'][0]
        vip_vmi.fetch()

        if 'instance_ip_back_refs' not in vip_vmi:
            printo('No IIP found for VIP VMI')
            return True

        return False

    def _remove_back_ref(self, r1, r2):
        printo('Remove back_ref from %s to %s' % (str(r1.path), str(r2.path)))
        if not self.dry_run:
            r1.remove_back_ref(r2)

    def _delete_res(self, r):
        printo('Delete %s' % str(r.path))
        if not self.dry_run:
            r.delete()

    def _clean_si(self, si):
        printo('Cleaning stale lbaas %s' % si.uuid)
        for pool in si.get('loadbalancer_pool_back_refs', []):
            pool.fetch()
            for vip in pool.get('virtual_ip_back_refs', []):
                vip.fetch()
                vip_vmis = vip.get('virtual_machine_interface_refs', [])
                self._delete_res(vip)
                for vmi in vip_vmis:
                    self._delete_res(vmi)
            self._remove_back_ref(si, pool)
        for vm in si.get('virtual_machine_back_refs', []):
            vm.fetch()
            for vr in vm.get('virtual_router_back_refs', []):
                self._remove_back_ref(vm, vr)
            for vmi in vm.get('virtual_machine_interface_back_refs', []):
                vmi.fetch()
                for fip in vmi.get('floating_ip_back_refs', []):
                    fip.fetch()
                    if len(fip['virtual_machine_interface_refs']) > 1:
                        self._remove_back_ref(vmi, fip)
                    else:
                        self._delete_res(fip)
                for iip in vmi.get('instance_ip_back_refs', []):
                    iip.fetch()
                    if len(iip['virtual_machine_interface_refs']) > 1:
                        self._remove_back_ref(vmi, iip)
                    else:
                        self._delete_res(iip)
                self._delete_res(vmi)
            self._delete_res(vm)
        self._delete_res(si)

    def __call__(self, paths=None, dry_run=False, check=False):
        self.dry_run = dry_run
        if not paths:
            resources = Collection('service-instance', fetch=True)
        else:
            resources = expand_paths(paths,
                                     predicate=lambda r: r.type == 'service-instance')
        for si in resources:
            si.fetch()
            try:
                si_t = si['service_template_refs'][0]
            except (KeyError, IndexError):
                printo('SI %s has no template, skipping.' % str(si.path))
                continue
            # don't use other SIs
            if 'haproxy-loadbalancer-template' not in si_t.fq_name:
                continue

            if self._is_stale(si):
                printo('Found stale lbaas %s (%s)' % (str(si.path), str(si.fq_name)))
                if check is not True:
                    self._clean_si(si)
