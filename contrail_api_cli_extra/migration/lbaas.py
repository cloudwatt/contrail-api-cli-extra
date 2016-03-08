# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg, expand_paths
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.utils import printo


class MigrateLbaas110221(Command):
    dry_run = Arg('--dry-run', '-n',
                  default=False,
                  action="store_true",
                  help='Run this command in dry-run mode')
    paths = Arg(nargs="*", help="LBaas SI path(s)",
                metavar='path')

    def _migrate_si(si):
        old_uuid = si.uuid
        old_fq_name = list(si.fq_name)

        # remove uuid to create a new resource
        del si['uuid']
        # compute the new fq_name
        si['fq_name'] = old_fq_name[:-1] + [old_fq_name[-1].split('_')[0]]
        si['display_name'] = old_fq_name[-1].split('_')[0]
        # create resource
        si.save()
        # migrate refs from old_si to new si
        old_si = Resource('service-instance', uuid=old_uuid, fetch=True)
        for vm in old_si.get('virtual_machine_back_refs', []):
            old_si.remove_back_ref(vm)
            si.add_back_ref(vm)
        for pool in old_si.get('loadbalancer_pool_back_refs', []):
            old_si.remove_back_ref(pool)
            si.add_back_ref(pool)
        # finally delete the old si
        old_si.delete()

    def __call__(self, paths=None, dry_run=False):
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
            printo('Found lbaas SI to migrate %s' % str(si.fq_name))
            if not dry_run:
                self._migrate_si(si)
