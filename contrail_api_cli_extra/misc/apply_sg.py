# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.command import Command, Option, Arg
from contrail_api_cli.resource import Resource


class ApplySG(Command):
    description = 'Apply security-group on virtual-machine-interface'
    project_fqname = Option(default="default-domain:default-project",
                            help='Project fqname (default: %(default)s)')
    vmi_name = Arg(help='VMI name')
    sg_name = Arg(help='SG name')

    def __call__(self, project_fqname=None, vmi_name=None, sg_name=None):
        sg_fqname = '%s:%s' % (project_fqname, sg_name)
        vmi_fqname = '%s:%s' % (project_fqname, vmi_name)

        sg = Resource('security-group', fq_name=sg_fqname, check=True)
        vmi = Resource('virtual-machine-interface',
                       fq_name=vmi_fqname,
                       fetch=True)
        for sg_ref in vmi.refs.security_group:
            vmi.remove_ref(sg_ref)
        vmi.add_ref(sg)
        vmi.save()
