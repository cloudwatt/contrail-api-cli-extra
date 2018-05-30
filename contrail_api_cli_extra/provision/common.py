# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def get_network_ipam_subnets(vn):
    if 'network_ipam_refs' not in vn:
        ipam_ref = {
            "attr": {
                "ipam_subnets": []
            },
            "to": ["default-domain", "default-project", "default-network-ipam"]
        }
        vn['network_ipam_refs'] = []
        vn['network_ipam_refs'].append(ipam_ref)
    return vn['network_ipam_refs'][0]['attr']['ipam_subnets']
