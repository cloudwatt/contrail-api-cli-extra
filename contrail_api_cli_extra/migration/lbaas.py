# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg, expand_paths
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.utils import printo, FQName


class MigrateLbaas110221(Command):
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

    def _migrate_si(self, si):
        old_uuid = si.uuid
        old_fq_name = list(si.fq_name)

        # remove uuid to create a new resource
        del si['uuid']
        # compute the new fq_name
        si['fq_name'] = FQName(old_fq_name[:-1] + [old_fq_name[-1].split('_')[0]])
        si['display_name'] = old_fq_name[-1].split('_')[0]
        # create resource
        self._create_res(si)
        # migrate refs from old_si to new si
        old_si = Resource('service-instance', uuid=old_uuid, fetch=True)
        for vm in old_si.get('virtual_machine_back_refs', []):
            self._remove_back_ref(old_si, vm)
            self._add_back_ref(si, vm)
        for pool in old_si.get('loadbalancer_pool_back_refs', []):
            self._remove_back_ref(old_si, pool)
            self._add_back_ref(si, pool)
        # finally delete the old si
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
                si_t = si['service_template_refs'][0]
            except (KeyError, IndexError):
                printo('SI %s has no template, skipping.' % si.uuid)
                continue
            # don't use other SIs
            if 'haproxy-loadbalancer-template' not in si_t.fq_name:
                continue
            # check old SI fq_name (two uuid) to migrate
            if not len(si.fq_name[-1].split('_')) == 2:
                continue
            printo('Found lbaas SI to migrate %s (%s)' % (si.path, si.fq_name))
            if not check:
                self._migrate_si(si)
