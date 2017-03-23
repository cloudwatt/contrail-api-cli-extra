# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging
import copy

from contrail_api_cli.client import ContrailAPISession
from contrail_api_cli.command import Command, Option, Arg, expand_paths
from contrail_api_cli.utils import continue_prompt
# from contrail_api_cli.exceptions import (CommandError,
# ResourceNotFound)
from contrail_api_cli.resource import Collection, Resource
from contrail_api_cli_extra.utils import CheckCommand, PathCommand
from novaclient import client as nclient

logger = logging.getLogger(__name__)

class UpdateQuota(CheckCommand, PathCommand):
    """Update a quota for tenant"""
    description = "Update a quota for a tenant"
    nova_api_version = Option('-v', default="2.1")
    yes = Option('-y', action='store_true',
                 help='Assume Yes to all queries and do not prompt')

    @property
    def resource_type(self):
        return "project"

    def _get_quota(self, project, default_project, quotas):
        output = {}
        for q in quotas:
            if "quota" in project.keys():
                if (q in project["quota"] and project["quota"][q] !='null'):
                    output.update({q: project["quota"][q]})
                else:
                    output.update({q: default_project["quota"][q]})
            else:
                    output.update({q: default_project["quota"][q]})
        return output

    def _get_usage(self, project, quotas):
        usages = {}
        for q in quotas:
            usages.update({q: len(Collection(q.replace('_','-'), parent_uuid=project.uuid, fetch=True))})
        return usages

    # def _update_quotas(self, quotas, quota_rules):
    def _update_quotas(self, quotas):
        quotas['loadbalancer_member'] = quotas['instances']
        quotas['loadbalancer_pool'] = quotas['loadbalancer_member']/2
        quotas['loadbalancer_healthmonitor'] = 0
        quotas['virtual_ip'] = quotas['loadbalancer_pool']
        return quotas

    def _check_quotas(self, quotas):
        new_quotas = self._update_quotas(quotas.copy())
        for k in new_quotas:
            if (quotas[k] == new_quotas[k]):
                logger.debug("Quota %s hasn't changed"% k)
                continue
            else:
                logger.debug("%s : old -> %s ; new -> %s ." % (k, quotas[k], new_quotas[k]))
                return False
                # continue
        return True

    def _set_quota(self, project, quotas, new_quotas):
        # Get lbaas usage
        neutron_lbaas_usage = self._get_usage(project, quotas)
        # print("Tenant %s usage." % p['display_name'])
        # print(neutron_lbaas_usage)

        # Check new lbaas quota are bigger than the number of spawned lbaas
        for q in quotas:
            if (int(neutron_lbaas_usage[q]) > int(new_quotas[q])):
                print("WARNING : Tenant %s has spawn more %s than the new value" % (project['display_name'], q))
                print("WARNING : Spawned %s : %i" % (q, neutron_lbaas_usage[q]))
                print("WARNING : New quota for %s: %i" % (q, new_quotas[q]))
                print("WARNING : Skipping update of quota %s for  tenant %s" % (q, project['display_name']))
            else:
                print("INFO : Tenant %s will have its quota %s set to %i" % (project['display_name'], q, new_quotas[q]))
                if not self.dry_run:
                    project['quota'][q] = new_quotas[q]
                    project.save()


    def __call__(self, nova_api_version=None, yes=False, **kwargs):
        super(UpdateQuota, self).__call__(**kwargs)
        self.nova = nclient.Client(nova_api_version, session=ContrailAPISession.session)
        default_project = Resource('project', fq_name='default-domain:default-project')
        default_project.fetch()
        lbaas_quota = ['virtual_ip', 'loadbalancer_pool', 'loadbalancer_member', 'loadbalancer_healthmonitor']
        technical_tenants = ('default-domain:default-project', 'default-domain:openstack')

        # TODO: It would be nice to apply some rules like this instead of hard-code them
        # lbaas_quota_rules = {'loadbalancer_member': 'instances'}
        # 'loadbalancer_pool': 'loadbalancer_member/2',
        # 'virtual_ip': 'loadbalancer_pool'}
        # 'loadbalancer_healthmonitor': '0'}

        for p in self.resources:
            p.fetch()
            # Don't touch "technical" tenants
            if (str(p['fq_name']) in technical_tenants):
                print("INFO : Skipping technical tenant %s." % str(p['fq_name']))
                continue
            if (not yes and
                not self.dry_run and
                not self.check and
                not continue_prompt("Do you want to update quotas for tenant %s ?" % p['display_name'])):
                print("Exiting.")
                exit()

            # Get nova quota
            nova_quota = self.nova.quotas.get(p.uuid.replace('-', '')).to_dict()

            # Get actual lbaas quota
            if 'quota' in p.keys():
                neutron_lbaas_quota = self._get_quota(p, default_project, lbaas_quota)
            else:
                print("INFO : Tenant %s use default quotas, skipping it" % p['display_name'])
                continue
            # for a in neutron_lbaas_quota:
                # print("%s : %s" %(a, neutron_lbaas_quota[a]))

            # Merge nova and neutron quota
            mixed_quota = neutron_lbaas_quota.copy()
            mixed_quota.update(nova_quota)
            # updated_quotas = self._update_quotas(mixed_quota, lbaas_quota_rules)

            # Check if quotas are compliant with lbaas quota rules

            if (self._check_quotas(mixed_quota)):
                # Nothing to do
                print("INFO : Quotas for tenant %s are good" % str(p['fq_name']))
            else:
                # Updating quotas
                updated_mixed_quotas = self._update_quotas(mixed_quota)
                # Get back neutron quota only
                updated_neutron_lbaas_quota = {}
                for q in lbaas_quota:
                    updated_neutron_lbaas_quota.update({q: updated_mixed_quotas[q]})
                # print("After update")
                # print(updated_neutron_lbaas_quota)
                self._set_quota(p, neutron_lbaas_quota, updated_neutron_lbaas_quota)
