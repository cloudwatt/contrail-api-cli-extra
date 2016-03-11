# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

from keystoneclient.exceptions import Conflict

from contrail_api_cli.commands import Command, Arg, expand_paths
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.utils import printo, FQName


class MigrateSI110221(Command):
    check = Arg('--check', '-c',
                default=False,
                action="store_true",
                help='Just check for LBaas SIs to migrate')
    dry_run = Arg('--dry-run', '-n',
                  default=False,
                  action="store_true",
                  help='Run this command in dry-run mode')
    paths = Arg(nargs="*", help="LBaas SI path(s)",
                metavar='path')

    def _remove_back_ref(self, r1, r2):
        printo('Remove back_ref from %s to %s' % (r1.path, r2.path))
        if not self.dry_run:
            r1.remove_back_ref(r2)

    def _add_back_ref(self, r1, r2):
        printo('Add back_ref from %s to %s' % (r1.path, r2.path))
        if not self.dry_run:
            r1.add_back_ref(r2)

    def _delete_res(self, r):
        printo('Delete %s' % r.path)
        if not self.dry_run:
            r.delete()

    def _create_res(self, r):
        printo('Create %s/%s' % (r.type, r.fq_name))
        if not self.dry_run:
            r.save()
            printo('Created %s' % r.path)

    def _migrate_vmi(self, old_vmi, old_vmi_index, new_vm, si):
        itf_type = old_vmi['virtual_machine_interface_properties']['service_interface_type']
        new_fq_name = list(si.parent.fq_name) + [str(new_vm.fq_name) + '__' + itf_type + '__' + str(old_vmi_index + 1)]

        vmi = copy.deepcopy(old_vmi)

        del vmi['uuid']
        del vmi['virtual_machine_refs']
        vmi['fq_name'] = FQName(new_fq_name)
        vmi['display_name'] = new_fq_name[-1]
        vmi['name'] = new_fq_name[-1]
        self._create_res(vmi)

        for iip in old_vmi.get('instance_ip_back_refs', []):
            self._remove_back_ref(old_vmi, iip)
            self._add_back_ref(vmi, iip)
        for fip in old_vmi.get('floating_ip_back_refs', []):
            self._remove_back_ref(old_vmi, fip)
            self._add_back_ref(vmi, fip)

        self._delete_res(old_vmi)

        return vmi

    def _migrate_vm(self, old_vm, old_vm_index, si):
        new_fq_name = '%s__%s__%s' % (str(si.parent.fq_name).replace(':', '__'), si.fq_name[-1], old_vm_index + 1)
        new_vm = Resource('virtual-machine',
                          fq_name=[new_fq_name],
                          display_name=new_fq_name + '__network-namespace',
                          name=new_fq_name)
        self._create_res(new_vm)

        for vr in old_vm.get('virtual_router_back_refs', []):
            self._remove_back_ref(old_vm, vr)
            self._add_back_ref(new_vm, vr)

        for idx, old_vmi in enumerate(old_vm.get('virtual_machine_interface_back_refs', [])):
            old_vmi.fetch()
            new_vmi = self._migrate_vmi(old_vmi, idx, new_vm, si)
            self._add_back_ref(new_vm, new_vmi)

        self._delete_res(old_vm)

        return new_vm

    def _migrate_si(self, old_si):
        si_target = old_si.get('loadbalancer_pool_back_refs', [None])[0]
        if si_target is not None:
            si_target_uuid = si_target.uuid
        elif si_target is None:
            si_target = old_si.get('logical_router_back_refs', [None])[0]
            si_target_uuid = old_si.fq_name[-1]

        if si_target is None:
            printo('No pool or router attached to SI')
            return

        new_si = Resource('service-instance',
                          fq_name=list(old_si.parent.fq_name) + [si_target_uuid],
                          display_name=si_target_uuid,
                          service_instance_properties=old_si['service_instance_properties'],
                          parent=old_si.parent)
        new_si['service_template_refs'] = old_si['service_template_refs']

        # SNAT si fq_name doesn't change so we create the same
        # resource and it will conflict
        re_use = False
        try:
            self._create_res(new_si)
        except Conflict:
            new_si = old_si
            re_use = True

        for old_vm_index, old_vm in enumerate(old_si.get('virtual_machine_back_refs', [])):
            old_vm.fetch()
            new_vm = self._migrate_vm(old_vm, old_vm_index, new_si)
            self._add_back_ref(new_si, new_vm)

        if not re_use:
            self._remove_back_ref(old_si, si_target)
            self._add_back_ref(new_si, si_target)
            self._delete_res(old_si)

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
                si['service_template_refs'][0]
            except (KeyError, IndexError):
                printo('SI %s has no template, skipping.' % si.uuid)
                continue
            vm = si.get('virtual_machine_back_refs', [None])[0]
            if vm is None:
                printo('SI %s has no VM, skipping.' % si.uuid)

            if si.fq_name[-1] in str(vm.fq_name):
                continue

            printo('Found lbaas SI to migrate %s (%s)' % (si.path, si.fq_name))
            if not check:
                self._migrate_si(si)
