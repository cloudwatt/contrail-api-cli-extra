# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.resource import Collection
from contrail_api_cli.resource import Resource

from contrail_api_cli.command import Option
from contrail_api_cli.utils import continue_prompt
from contrail_api_cli.exceptions import CommandError

from ..utils import CheckCommand


class FixSg(CheckCommand):
    description = "Fix default security group that shouldn't belong to a project"
    yes = Option('-y', action='store_true', help='Assume Yes to all queries and do not prompt')
    long_description = """ It appears sometimes several default security groups have been
    created. Normally, only one default security group should be
    created. When there are several security groups, some of them
    doesn't have the right project name in their fq_name. These
    secrutiy group are not legitimate.

    The check mode of this script detects these security groups and
    marks default security groups of a tenant as good or bad. Good
    default security group is legitimate while bad are not. Moreover,
    if it exists bad security groups, the scripts returns 1 otherwise,
    it returns 0.

    Concerning normal mode and dry-run mode, the script tries to
    delete non used bad default security groups. "Non used" means no
    VMIs are attached to them.
    """

    def _handle_sg(self, status, sg_dict, delete=True):
        print "    %s  SG: %s %s" % (status, sg_dict['uuid'], ":".join(sg_dict['to']))
        if not self.check:
            used = False
            sg = Resource("security-group", uuid=sg_dict['uuid'], fetch=True)
            for br in sg.back_refs:
                used = True
                print "        Used by VMI %s" % br.uuid
            if not used and delete:
                if not self.dry_run:
                    print "            Deleting SG %s ..." % sg.uuid
                    sg.delete()
                else:
                    print "            [dry-run] Deleting SG %s ..." % sg.uuid

    def __call__(self, yes=False, **kwargs):
        super(FixSg, self).__call__(**kwargs)
        if (not yes and
                not self.dry_run and
                not self.check and
                not continue_prompt("Some SGs will be deleted. Are you sure to continue?")):
            raise CommandError("Exiting.")

        bad_sg_exists = False
        col = Collection("project")
        col.fetch()
        for r in col:
            r.fetch()
            fq_name = r.fq_name
            if 'security_groups' in r:
                bad_sg = []
                good_sg = []
                for sg in r.data['security_groups']:
                    if sg['to'][2] == 'default':
                        if str(":".join(sg['to'][0:2])) != str(fq_name):
                            bad_sg.append(sg)
                        else:
                            good_sg.append(sg)
                if bad_sg != []:
                    bad_sg_exists = True
                    print "Tenant       %s %s" % (r.uuid, r.fq_name)
                    for sg in bad_sg:
                        self._handle_sg("Bad ", sg)
                    for sg in good_sg:
                        self._handle_sg("Good", sg, delete=False)

        if self.check and bad_sg_exists:
            raise CommandError()
