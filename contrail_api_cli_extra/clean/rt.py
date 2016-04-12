# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.command import Command, Arg, expand_paths
from contrail_api_cli.resource import Collection
from contrail_api_cli.utils import printo, parallel_map
from contrail_api_cli.client import HTTPError


class CleanStaleRT(Command):
    check = Arg('--check', '-c',
                default=False,
                action="store_true",
                help='Just check for stale RT')
    dry_run = Arg('--dry-run', '-n',
                  default=False,
                  action="store_true",
                  help='Run this command in dry-run mode')
    paths = Arg(nargs="*", help="RT path(s)",
                metavar='path')

    def _clean_rt(self, rt):
        if not self.dry_run:
            rt.delete()
        printo("Removed RT %s" % rt.path)

    def _check_rt(self, rt, check):
        try:
            rt.fetch()
        except HTTPError:
            return
        if not rt.get('routing_instance_back_refs') and not rt.get('logical_router_back_refs'):
            printo('RT %s (%s) staled' % (rt.path, rt.fq_name))
            if check is not True:
                self._clean_rt(rt)

    def __call__(self, paths=None, dry_run=False, check=False):
        self.dry_run = dry_run
        if not paths:
            resources = Collection('route-target', fetch=True)
        else:
            resources = expand_paths(paths,
                                     predicate=lambda r: r.type == 'route-target')
        parallel_map(self._check_rt, resources, args=(check,), workers=50)
