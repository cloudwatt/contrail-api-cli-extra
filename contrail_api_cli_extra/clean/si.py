# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.command import Command, Arg, expand_paths
from contrail_api_cli.resource import Collection
from contrail_api_cli.utils import printo, parallel_map
from contrail_api_cli.client import HTTPError


class CleanSIScheduling(Command):
    check = Arg('--check', '-c',
                default=False,
                action="store_true",
                help='Just check for bad SI scheduling')
    dry_run = Arg('--dry-run', '-n',
                  default=False,
                  action="store_true",
                  help='Run this command in dry-run mode')
    paths = Arg(nargs="*", help="SI path(s)",
                metavar='path')

    def _clean_vm(self, vm):
        for vr in vm.get('virtual_router_back_refs')[1:]:
            if not self._dry_run:
                vm.remove_back_ref(vr)
            printo("Removed %s from %s" % (vr.fq_name, vm.uuid))

    def _check_si(self, si, check):
        try:
            si.fetch()
        except HTTPError:
            return
        for vm in si.get('virtual_machine_back_refs', []):
            vm.fetch()
            if len(vm.get('virtual_router_back_refs', [])) > 1:
                printo('SI %s VM %s is scheduled on %s' % (
                    si.path,
                    vm.uuid,
                    ", ".join([str(vr.fq_name) for vr in vm['virtual_router_back_refs']])))
                if check is not True:
                    self._clean_vm(vm)

    def __call__(self, paths=None, dry_run=False, check=False):
        self.dry_run = dry_run
        if not paths:
            resources = Collection('service-instance', fetch=True)
        else:
            resources = expand_paths(paths,
                                     predicate=lambda r: r.type == 'service-instance')
        parallel_map(self._check_si, resources, args=(check,), workers=50)
