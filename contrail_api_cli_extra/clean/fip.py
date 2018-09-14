# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.command import Option
from contrail_api_cli.utils import printo
from contrail_api_cli.exceptions import ResourceNotFound

from ..utils import CassandraCommand, CheckCommand, PathCommand
from refs import CleanRefs

class CleanFipRefs(CassandraCommand, CheckCommand, PathCommand):
    """Clean broken references related to floating IPs.

    Broken refs related to FIP can be found with gremlin (floating-ip-pool <->
    floating-ip).

    The command will take all existing floating-ip-pool and checks the existence
    of each floating-ip it points to and removes the reference if that latter
    does not exist.

    You can run the command by putting the floating-ip-pool path to be more
    precise or you can run it without any resources path, in that case it will
    iterates over all floating-ip-pool.

    You can also specify the floating-ip uuids refs list you want to clean,
    and it will remove those floating-ip references only for the floating-ip-pool
    where the floating-ip is linked to.

    """
    description = "Clean broken references related to floating IPs"

    refs = Option(help="list of floating IP UUIDs", nargs="*", default=[])

    @property
    def resource_type(self):
        return "floating-ip-pool"

    def _clean_refs(self, pool, fip, **kwargs):
        try:
            fip.fetch()
        except ResourceNotFound:
            CleanRefs(ref_type="children",
                      target_type="floating_ip",
                      paths=[pool.uuid, fip.uuid],
                      **kwargs)

    def __call__(self, refs, **kwargs):
        super(CleanFipRefs, self).__call__(**kwargs)
        for pool in self.resources:
            try:
                pool.fetch()
                if refs:
                    fip_list = [fip for fip in pool.children.floating_ip if
                                fip.uuid in refs]
                else:
                    fip_list = pool.children.floating_ip

                for fip in fip_list:
                    # TODO: clean also refs between project and fip by using
                    #       projects = Collection('project',
                    #                             fetch=True,
                    #                             back_refs_uuid=['2f20ee42-c69a-4521-800c-d0a151bdf93d'])
                    self._clean_refs(pool, fip, **kwargs)

            except ResourceNotFound as e:
                printo(e)
