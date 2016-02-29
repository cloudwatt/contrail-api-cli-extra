# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Collection
from contrail_api_cli.utils import printo


class CleanStaleLBaasSI(Command):
    dry_run = Arg('--dry-run', '-n',
                  default=False,
                  action="store_true",
                  help='Run this command in dry-run mode')

    def __call__(self, dry_run=False):
        service_instances = Collection('service-instance', fetch=True)
        for si in service_instances:
            si.fetch()

            if 'loadbalancer_pool_back_refs' in si:
                continue
            if 'logical_router_back_refs' in si:
                continue

            printo('Found stale SI %s' % str(si.path))

            for vm in si.get('virtual_machine_back_refs', []):
                vm.fetch()
                for vr in vm.get('virtual_router_back_refs', []):
                    vr.fetch()
                    for vm_ref in vr.get('virtual_machine_refs', []):
                        if vm_ref.uuid == vm.uuid:
                            vr['virtual_machine_refs'].remove(vm_ref)
                            printo('Remove ref from %s to %s' % (vr.path, vm.path))
                            if not dry_run:
                                vr.save()
                            break
                for vmi in vm.get('virtual_machine_interface_back_refs', []):
                    vmi.fetch()
                    for fip in vmi.get('floating_ip_back_refs', []):
                        fip.fetch()
                        for vmi_ref in fip.get('virtual_machine_interface_refs', []):
                            if vmi_ref.uuid == vmi.uuid:
                                fip['virtual_machine_interface_refs'].remove(vmi_ref)
                                printo('Remove ref from %s to %s' % (fip.path, vmi.path))
                                if not dry_run:
                                    fip.save()
                                break
                    for iip in vmi.get('instance_ip_back_refs', []):
                        printo('Delete %s' % str(iip.path))
                        if not dry_run:
                            iip.delete()
                    printo('Delete %s' % str(vmi.path))
                    if not dry_run:
                        vmi.delete()
                printo('Delete %s' % str(vm.path))
                if not dry_run:
                    vm.delete()
            printo('Delete %s' % str(si.path))
            if not dry_run:
                si.delete()
