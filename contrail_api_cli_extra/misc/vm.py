# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools
import logging
from six import text_type

from contrail_api_cli.command import Arg, expand_paths
from contrail_api_cli.utils import printo

from contrail_api_cli_extra.utils import CheckCommand


logger = logging.getLogger(__name__)


class RescheduleVM(CheckCommand):
    """Command to move a SI VMs from one virtual-router to other virtual-routers.

    This command will move all SI VMs found on the provided VR to a
    list of VRs. The command will make sure two VMs of the same SI
    will not end up on the same VR.

    The command can be run in dry-run mode to see how the VMs will be moved.

    To reschedule VMs run::

        contrail-api-cli reschedule-vm virtual-router/uuid1 virtual-router/uuid2 virtual-router/uuid3

    This will move all VR/uuid1 SI VMs to VR/uuid2 and VR/uuid3 evenly.
    """

    description = "Move SI VMs from one virtual-router to other virtual-router(s)"
    src = Arg(help='source vrouter path',
              complete='resources:virtual-router:path')
    dst = Arg(help='destination vrouters paths', nargs='+',
              complete='resources:virtual-router:path')

    def __call__(self, src=None, dst=None, **kwargs):
        super(RescheduleVM, self).__call__(**kwargs)
        src = expand_paths([src],
                           predicate=lambda r: r.type == 'virtual-router')[0]
        dst = expand_paths(dst,
                           predicate=lambda r: r.type == 'virtual-router')

        # get list of VMs to move
        vms = []
        src.fetch()
        for vm in src.refs.virtual_machine:
            vm.fetch()
            if vm.refs.service_instance:
                vms.append((0, vm))

        if not vms:
            return "No VMs on this virtual-router"

        if self.check:
            return "\n".join([text_type(vm.path) for (_, vm) in vms])

        # get all the resources we need
        for vr in dst:
            vr.fetch()
            for vm in vr.refs.virtual_machine:
                vm.fetch()

        printo("Moving %d VMs from %s to %s" %
               (len(vms), src['name'], ", ".join([vr['name'] for vr in dst])))

        for vr in itertools.cycle(dst):
            # no more VMs to process
            if not vms:
                break
            failures, vm = vms.pop(0)
            vm_si = vm.refs.service_instance[0]
            vr_sis = [si
                      for vr_vm in vr.refs.virtual_machine
                      for si in vr_vm.refs.service_instance]
            logger.debug("Checking VM %s of SI %s" % (vm, vm_si))
            if vm_si in vr_sis:
                logger.debug("%s already has a VM for SI %s" % (vr['name'], vm_si))
                if failures == len(dst):
                    printo("Unable to move VM %s. Dest vrouter already has a VM of the same SI." % vm)
                else:
                    vms.insert(0, (failures + 1, vm))
            else:
                printo("Moving VM %s on %s" % (vm, vr['name']))
                if not self.dry_run:
                    src.remove_ref(vm)
                    vr.add_ref(vm)
