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

            # SI linked to a LBaas pool, skiping
            if 'loadbalancer_pool_back_refs' in si:
                continue
            # skip on SNAT SIs
            if 'si_' in str(si.fq_name) or 'snat_' in str(si.fq_name):
                continue

            printo('Found stale SI %s' % str(si.path))
            si.fetch()

            for vm in si.get('virtual_machine_back_refs', []):
                vm.fetch()
                for vr in vm.get('virtual_router_back_refs', []):
                    printo('Remove back_ref from %s to %s' % (str(vm.path), str(vr.path)))
                    vm.remove_back_ref(vr)
                for vmi in vm.get('virtual_machine_interface_back_refs', []):
                    vmi.fetch()
                    for fip in vmi.get('floating_ip_back_refs', []):
                        fip.fetch()
                        if len(fip['virtual_machine_interface_refs']) > 1:
                            printo('Remove back_ref from %s to %s' % (str(vmi.path), str(fip.path)))
                            if not dry_run:
                                vmi.remove_back_ref(fip)
                        else:
                            printo('Delete %s' % str(fip.path))
                            if not dry_run:
                                fip.delete()
                    for iip in vmi.get('instance_ip_back_refs', []):
                        iip.fetch()
                        if len(iip['virtual_machine_interface_refs']) > 1:
                            printo('Remove back_ref from %s to %s' % (str(vmi.path), str(iip.path)))
                            if not dry_run:
                                vmi.remove_back_ref(iip)
                        else:
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
