# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

from keystoneclient.exceptions import Conflict

from contrail_api_cli.command import Arg, expand_paths
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.utils import printo, FQName
from contrail_api_cli.schema import require_schema

from ..utils import CheckCommand


class MigrateSI110221(CheckCommand):
    """Migration command for SI from 1.10 version to 2.21 version
    """
    description = 'Migrate SIs from 1.10 to 2.21'
    paths = Arg(nargs="*", help="SI path(s)",
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

    def _migrate_iip(self, old_iip, si, itf_type):
        new_fq_name = '%s__%s-%s' % (str(si.parent.fq_name).replace(':', '__'), si.fq_name[-1], itf_type)

        # there is 2 left itf so migrate the iip only once
        if str(old_iip.fq_name) == new_fq_name:
            printo('Already migrated %s. Skip' % old_iip.fq_name)
            return old_iip

        self._delete_res(old_iip)
        iip = copy.deepcopy(old_iip)

        del iip['uuid']
        iip['fq_name'] = FQName([new_fq_name])
        iip['display_name'] = new_fq_name
        iip['name'] = new_fq_name
        self._create_res(iip)

        return iip

    def _migrate_vmi(self, old_vmi, new_vm, si):
        itf_type = old_vmi['virtual_machine_interface_properties']['service_interface_type']
        if itf_type == 'right':
            vmi_index = str(1)
        else:
            vmi_index = str(2)
        new_fq_name = list(si.parent.fq_name) + [str(new_vm.fq_name) + '__' + itf_type + '__' + vmi_index]

        vmi = copy.deepcopy(old_vmi)

        del vmi['uuid']
        vmi['fq_name'] = FQName(new_fq_name)
        vmi['display_name'] = new_fq_name[-1]
        vmi['name'] = new_fq_name[-1]
        self._create_res(vmi)

        for old_iip in old_vmi.get('instance_ip_back_refs', []):
            self._remove_back_ref(old_vmi, old_iip)
            new_iip = self._migrate_iip(old_iip, si, itf_type)
            self._add_back_ref(vmi, new_iip)

        for fip in old_vmi.get('floating_ip_back_refs', []):
            self._remove_back_ref(old_vmi, fip)
            self._add_back_ref(vmi, fip)

        self._delete_res(old_vmi)

        return vmi

    def _migrate_vm(self, old_vm, old_vm_index, si):
        new_fq_name = '%s__%s__%s' % (str(si.parent.fq_name).replace(':', '__'), si.fq_name[-1], old_vm_index)
        new_vm = Resource('virtual-machine',
                          fq_name=[new_fq_name],
                          display_name=new_fq_name + '__network-namespace',
                          name=new_fq_name)
        try:
            self._create_res(new_vm)
        except Conflict:
            return old_vm

        for vr in old_vm.get('virtual_router_back_refs', []):
            self._remove_back_ref(old_vm, vr)
            self._add_back_ref(new_vm, vr)

        for old_vmi in old_vm.get('virtual_machine_interface_back_refs', []):
            old_vmi.fetch()
            self._remove_back_ref(old_vm, old_vmi)
            new_vmi = self._migrate_vmi(old_vmi, new_vm, si)
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

        for old_vm in old_si.get('virtual_machine_back_refs', []):
            old_vm.fetch()
            self._remove_back_ref(old_si, old_vm)
            # VM index is the last char of the fq_name
            new_vm = self._migrate_vm(old_vm, str(old_vm.fq_name)[-1], new_si)
            self._add_back_ref(new_si, new_vm)

        if not re_use:
            self._remove_back_ref(old_si, si_target)
            self._delete_res(old_si)
            self._add_back_ref(new_si, si_target)

    @require_schema(version='1.10')
    def __call__(self, paths=None, **kwargs):
        super(MigrateSI110221, self).__call__(**kwargs)
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
            vms = si.get('virtual_machine_back_refs', [])
            if not vms:
                printo('SI %s has no VM, skipping.' % si.uuid)

            if all([si.fq_name[-1] in str(vm.fq_name) for vm in vms]):
                continue

            printo('Found lbaas SI to migrate %s (%s)' % (si.path, si.fq_name))
            if not self.check:
                self._migrate_si(si)
                printo('Done')
