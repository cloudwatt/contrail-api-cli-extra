# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.utils import printo, parallel_map
from contrail_api_cli.exceptions import ResourceNotFound

from ..utils import CheckCommand, PathCommand


class CleanSIScheduling(CheckCommand, PathCommand):
    """On some occasion a SI VM can be scheduled on multiple virtual-routers.

    In such case the command will remove extraenous VR links on the SI VM::

        contrail-api-cli --ns contrail_api_cli.clean clean-si-scheduling [service-instance/uuid]

    ``--check`` and ``--dry-run`` options are available.
    """
    description = "Clean bad vrouter scheduling"

    @property
    def resource_type(self):
        return "service-instance"

    def _clean_vm(self, vm):
        for vr in vm.get('virtual_router_back_refs')[1:]:
            if not self.dry_run:
                vm.remove_back_ref(vr)
            printo("Removed %s from %s" % (vr.fq_name, vm.uuid))

    def _check_si(self, si):
        try:
            si.fetch()
        except ResourceNotFound:
            return
        for vm in si.get('virtual_machine_back_refs', []):
            vm.fetch()
            if len(vm.get('virtual_router_back_refs', [])) > 1:
                printo('SI %s VM %s is scheduled on %s' % (
                    si.path,
                    vm.uuid,
                    ", ".join([str(vr.fq_name) for vr in vm['virtual_router_back_refs']])))
                if self.check is not True:
                    self._clean_vm(vm)

    def __call__(self, paths=None, **kwargs):
        super(CleanSIScheduling, self).__call__(**kwargs)
        parallel_map(self._check_si, self.resources, workers=50)


class CleanStaleSI(CheckCommand, PathCommand):
    """Clean stale service instances.

    SIs are considered stale when:

    * LBaaS SI has no pool
    * LBaaS SI pool has no VIP
    * LBaas SI VIP has no instance-ip
    * SNAT SI has no logical-router

    To run the command::

        contrail-api-cli --ns contrail_api_cli.ns clean-stale-si [service-instance/uuid]

    ``--check`` and ``--dry-run`` options are available.
    """
    description = "Clean stale SIs"

    @property
    def resource_type(self):
        return "service-instance"

    def _is_stale_snat(self, si):
        """Return True if the snat SI is stale.
        """
        if 'logical_router_back_refs' not in si:
            printo('[%s] No logical router attached to SI' % si.uuid)
            return True

        return False

    def _is_stale_lbaas(self, si):
        """Return True if the lbaas SI is stale.
        """

        if 'loadbalancer_pool_back_refs' not in si:
            printo('[%s] No pool attached to SI' % si.uuid)
            return True

        pool = si['loadbalancer_pool_back_refs'][0]
        pool.fetch()

        if 'virtual_ip_back_refs' not in pool:
            printo('[%s] No VIP attached to pool' % si.uuid)
            return True

        vip = pool['virtual_ip_back_refs'][0]
        vip.fetch()

        if 'virtual_machine_interface_refs' not in vip:
            printo('[%s] No VMI for VIP' % si.uuid)
            return True

        vip_vmi = vip['virtual_machine_interface_refs'][0]
        vip_vmi.fetch()

        if 'instance_ip_back_refs' not in vip_vmi:
            printo('[%s] No IIP found for VIP VMI' % si.uuid)
            return True

        return False

    def _remove_back_ref(self, si, r1, r2):
        printo('[%s] Remove back_ref from %s to %s' % (si.uuid, str(r1.path), str(r2.path)))
        if not self.dry_run:
            r1.remove_back_ref(r2)

    def _delete_res(self, si, r):
        printo('[%s] Delete %s' % (si.uuid, str(r.path)))
        if not self.dry_run:
            r.delete()

    def _clean_lbaas_si(self, si):
        printo('[%s] Cleaning stale lbaas' % si.uuid)
        for pool in si.get('loadbalancer_pool_back_refs', []):
            pool.fetch()
            for vip in pool.get('virtual_ip_back_refs', []):
                vip.fetch()
                vip_vmis = vip.get('virtual_machine_interface_refs', [])
                self._delete_res(si, vip)
                for vmi in vip_vmis:
                    self._delete_res(si, vmi)
            self._remove_back_ref(si, si, pool)

    def _clean_si(self, si):
        for vm in si.get('virtual_machine_back_refs', []):
            vm.fetch()
            for vr in vm.get('virtual_router_back_refs', []):
                self._remove_back_ref(si, vm, vr)
            for vmi in vm.get('virtual_machine_interface_back_refs', []):
                vmi.fetch()
                for fip in vmi.get('floating_ip_back_refs', []):
                    fip.fetch()
                    if len(fip['virtual_machine_interface_refs']) > 1:
                        self._remove_back_ref(si, vmi, fip)
                    else:
                        self._delete_res(si, fip)
                for iip in vmi.get('instance_ip_back_refs', []):
                    iip.fetch()
                    if len(iip['virtual_machine_interface_refs']) > 1:
                        self._remove_back_ref(si, vmi, iip)
                    else:
                        self._delete_res(si, iip)
                self._delete_res(si, vmi)
            self._delete_res(si, vm)
        self._delete_res(si, si)

    def _check_si(self, si):
        si.fetch()
        try:
            si_t = si['service_template_refs'][0]
        except (KeyError, IndexError):
            printo('[%s] SI %s has no template, skipping.' % (si.uuid, str(si.path)))
            return

        if 'haproxy-loadbalancer-template' in si_t.fq_name and self._is_stale_lbaas(si):
            printo('[%s] Found stale lbaas %s' % (si.uuid, str(si.fq_name)))
            if self.check is not True:
                self._clean_lbaas_si(si)
                self._clean_si(si)

        if 'netns-snat-template' in si_t.fq_name and self._is_stale_snat(si):
            printo('[%s] Found stale SNAT %s' % (si.uuid, str(si.fq_name)))
            if self.check is not True:
                self._clean_si(si)

    def __call__(self, paths=None, **kwargs):
        super(CleanStaleSI, self).__call__(**kwargs)
        parallel_map(self._check_si, self.resources, workers=50)
