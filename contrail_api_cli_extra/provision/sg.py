# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import argparse
import json
import uuid
import netaddr
from six import text_type

from contrail_api_cli.command import Command, Option, Arg
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.utils import FQName


def _port_or_default(port):
    if port in [0, 65535]:
        return ""
    return text_type(port)


def _remote_cidr_or_default(cidr):
    if cidr == "0.0.0.0/0":
        return ""
    return cidr


class SG(Command):
    project_fqname = Option(default="default-domain:default-project",
                            help='Project fqname (default: %(default)s)')


class SGAction(SG):
    security_group_name = Arg(help='Security group name')


def rule_type(string):
    """argparse type to validate SG rule.
    """
    try:
        direction, proto, port_min, port_max, remote_cidr = string.split(":")
    except Exception as e:
        raise argparse.ArgumentTypeError('Bad SG rule format: %s' % e)
    if direction not in ["ingress", "egress"]:
        raise argparse.ArgumentTypeError("Direction must be 'ingress' or 'egress'")
    if proto not in ["", "tcp", "udp", "icmp"]:
        raise argparse.ArgumentTypeError("Proto must be 'tcp', 'udp', 'icmp' or ''")
    if remote_cidr == "0.0.0.0/0":
        raise argparse.ArgumentTypeError('Use empty value instead of 0.0.0.0/0 for remote_cidr')
    try:
        if remote_cidr:
            netaddr.IPNetwork(remote_cidr)
        else:
            remote_cidr = "0.0.0.0/0"
    except netaddr.AddrFormatError:
        raise argparse.ArgumentTypeError('%s is not a network' % remote_cidr)
    if not port_min:
        port_min = 0
    elif port_min == 0:
        raise argparse.ArgumentTypeError('Use empty value instead of 0 for port_min')
    if not port_max:
        port_max = 65535
    elif port_max == 65535:
        raise argparse.ArgumentTypeError('Use empty value instead of 65535 for port_max')
    return {
        "direction": direction,
        "proto": proto,
        "port_min": int(port_min),
        "port_max": int(port_max),
        "remote_cidr": netaddr.IPNetwork(remote_cidr),
    }


class AddSG(SGAction):
    description = 'Add security-group'
    rule = Option(action='append',
                  dest='rules',
                  default=[],
                  type=rule_type,
                  help='SG rule format: direction:proto:port_min:port_max:remote_cidr')

    def _rule_to_policy(self, rule):
        policy = {
            "action_list": None,
            "application": [],
            "direction": ">",
            "ethertype": "IPv4",
            "protocol": rule['proto'],
            "rule_sequence": None,
            "rule_uuid": text_type(uuid.uuid4()),
        }
        local_addr = [{
            "network_policy": None,
            "security_group": "local",
            "subnet": None,
            "virtual_network": None,
        }]
        target_addr = [{
            "network_policy": None,
            "security_group": None,
            "subnet": {
                "ip_prefix": text_type(rule['remote_cidr'].ip),
                "ip_prefix_len": int(rule['remote_cidr'].prefixlen),
            },
            "virtual_network": None,
        }]
        all_ports = [{"start_port": 0, "end_port": 65535}]
        rule_ports = [{"start_port": rule['port_min'], "end_port": rule['port_max']}]

        if rule['direction'] == "ingress":
            policy["src_addresses"] = target_addr
            policy["src_ports"] = all_ports
            policy["dst_addresses"] = local_addr
            policy["dst_ports"] = rule_ports
        else:
            policy["src_addresses"] = local_addr
            policy["src_ports"] = all_ports
            policy["dst_addresses"] = target_addr
            policy["dst_ports"] = rule_ports

        return policy

    def __call__(self, project_fqname=None, security_group_name=None, rules=None):
        sg_fqname = '%s:%s' % (project_fqname, security_group_name)

        # fetch project to sync it from keystone if not already there
        project = Resource('project', fq_name=project_fqname, fetch=True)
        sg = Resource('security-group',
                      fq_name=sg_fqname,
                      parent=project)
        for rule in rules:
            if "security_group_entries" not in sg:
                sg["security_group_entries"] = {"policy_rule": []}
            sg["security_group_entries"]["policy_rule"].append(self._rule_to_policy(rule))

        sg.save()


class DelSG(SGAction):
    description = 'Delete security-group'

    def __call__(self, project_fqname=None, security_group_name=None, **kwargs):
        sg_fqname = '%s:%s' % (project_fqname, security_group_name)
        sg = Resource('security-group', fq_name=sg_fqname, check=True)
        sg.delete()


class ListSGs(SG):
    description = 'List security-groups'

    def _policy_to_rule(self, policy):
        rule = []
        if policy["src_addresses"][0]["security_group"] == "local":
            rule.append("egress")
            rule.append(policy['protocol'])
            rule.append(_port_or_default(policy["dst_ports"][0]["start_port"]))
            rule.append(_port_or_default(policy["dst_ports"][0]["end_port"]))
            rule.append(_remote_cidr_or_default("%s/%s" % (policy["dst_addresses"][0]["subnet"]["ip_prefix"], policy["dst_addresses"][0]["subnet"]["ip_prefix_len"])))
        else:
            rule.append("ingress")
            rule.append(policy['protocol'])
            rule.append(_port_or_default(policy["dst_ports"][0]["start_port"]))
            rule.append(_port_or_default(policy["dst_ports"][0]["end_port"]))
            rule.append(_remote_cidr_or_default("%s/%s" % (policy["src_addresses"][0]["subnet"]["ip_prefix"], policy["src_addresses"][0]["subnet"]["ip_prefix_len"])))
        return ":".join(rule)

    def __call__(self, project_fqname=None):
        project = Resource('project', fq_name=project_fqname, check=True)
        sgs = Collection('security-group',
                         parent_uuid=project.uuid,
                         fetch=True, detail=True)

        return json.dumps([{
            "project_fqname": str(FQName(sg.fq_name[0:-1])),
            "security_group_name": str(sg.fq_name[-1]),
            "rules": [self._policy_to_rule(p)
                      for p in sg.get("security_group_entries", {}).get("policy_rule", [])],
        } for sg in sgs], indent=2)
