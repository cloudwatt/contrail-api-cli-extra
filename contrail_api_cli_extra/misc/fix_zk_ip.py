# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from netaddr import IPNetwork, IPAddress
from contrail_api_cli.command import Option
from contrail_api_cli.resource import Resource
from contrail_api_cli.utils import continue_prompt, printo, parallel_map
from contrail_api_cli.exceptions import CommandError, ResourceNotFound

import logging
import uuid

from ..utils import ZKCommand, CheckCommand, PathCommand

logger = logging.getLogger(__name__)


class FixZkIP(ZKCommand, CheckCommand, PathCommand):
    description = "Remove zookeeper locks for IPs not present in Contrail API"
    yes = Option('-y', action='store_true',
                 help='Assume Yes to all queries and do not prompt')

    @property
    def resource_type(self):
        return "virtual-network"

    def _zk_node_for_subnet(self, fqname, prefix, prefix_len):
        return ('/api-server/subnets/{0}:{1}/{2}'
                .format(fqname, prefix, prefix_len))

    def _zk_node_for_ip(self, fqname, prefix, prefix_len, ip):
        return ('/api-server/subnets/{0}:{1}/{2}/{3}'
                .format(fqname, prefix, prefix_len, int(ip)))

    def _get_subnet(self, virtual_network):
        subnet = []
        vn_subnet = (virtual_network['network_ipam_refs'][0]
                                    ['attr']['ipam_subnets'])
        for s in vn_subnet:
            prefix = s['subnet']['ip_prefix']
            prefix_len = s['subnet']['ip_prefix_len']
            subnet.append((IPNetwork(str(prefix) + '/' + str(prefix_len))))
        return subnet

    def _get_subnet_for_ip(self, ip, subnets):
        for subnet in subnets:
            if ip in subnet:
                return subnet

    def get_zk_ip(self, virtual_network):
        zk_ips = {}
        fq_name = str(virtual_network.fq_name)
        if len(virtual_network['network_ipam_refs']
                              [0]['attr']['ipam_subnets']) == 0:
            raise CommandError('No subnet defined for {0}'.format(fq_name))
            return zk_ips
        for s in self._get_subnet(virtual_network):
            zk_subnet_req = self._zk_node_for_subnet(
                                fq_name,
                                str(s.network),
                                str(s.prefixlen)
                            )
            for _ip in self.zk_client.get_children(zk_subnet_req):
                try:
                    zk_ip = IPAddress(_ip)
                except:
                    logger.warning('{0} INVALID IP : zk_path={1}/{2}'
                                   .format(str(_ip), zk_subnet_req, str(_ip)))
                    print('{0} INVALID IP : zk_path={1}/{2}'
                          .format(str(_ip), zk_subnet_req, str(_ip)))
                    continue

                check_consistant_ip = self._get_subnet_for_ip(zk_ip, [s])
                if check_consistant_ip:
                    zk_ips[str(zk_ip)] = zk_subnet_req + '/' + _ip
                else:
                    logger.warning('{0} OUT OF RANGE {1} : zk_path={2}/{3}'
                                   .format(str(zk_ip),
                                           str(s.cidr),
                                           zk_subnet_req, int(zk_ip)))
                    print('{0} OUT OF RANGE : zk_path={1}/{2}'
                          .format(str(zk_ip), zk_subnet_req, str(_ip)))
        return zk_ips

    def get_api_ip(self, virtual_network):
        api_ips = {}
        fq_name = str(virtual_network.fq_name)
        if len(virtual_network['network_ipam_refs'][0]
                              ['attr']['ipam_subnets']) == 0:
            raise CommandError('No subnet defined for {0}'.format(fq_name))
            return api_ips

        vn_subnet = (virtual_network['network_ipam_refs'][0]
                                    ['attr']['ipam_subnets'])
        for s in vn_subnet:
            prefix = s['subnet']['ip_prefix']
            prefix_len = s['subnet']['ip_prefix_len']
            subnet = (IPNetwork(str(prefix) + '/' + str(prefix_len)))
            api_ips[str(subnet.network)] = virtual_network
            api_ips[str(subnet.broadcast)] = virtual_network
            # Some networks do have dns and gateway IPs
            if 'default_gateway' in s:
                api_ips[str(IPAddress(s['default_gateway']))] = virtual_network
            if 'dns_server_address' in s:
                api_ips[str(IPAddress(
                        s['dns_server_address']))] = virtual_network
        if 'instance_ip_back_refs' in virtual_network:
            for iip in virtual_network.back_refs.instance_ip:
                iip.fetch()
                api_ips[str(IPAddress(iip['instance_ip_address']))] = iip
        if 'floating_ip_pools' in virtual_network:
            logger.debug(str(virtual_network.fq_name) + " is a public network")
            for pool in virtual_network.children.floating_ip_pool:
                pool.fetch()
                for fip in pool.children.floating_ip:
                    fip.fetch()
                    api_ips[str(IPAddress(fip['floating_ip_address']))] = fip
        return api_ips

    def add_znode_ip(self, ip, resource, dry_run=True):
        if resource.type == 'floating-ip':
            self.add_znode_fip(resource, dry_run)
        elif resource.type == 'instance-ip':
            self.add_znode_iip(resource, dry_run)
        elif resource.type == 'virtual-network':
            self.add_znode_reserved_ip(ip, resource, dry_run)
        else:
            print('Unknow type for ip {0}'.format(ip))

    def add_znode_iip(self, iip, dry_run=True):
        ip = IPAddress(iip['instance_ip_address'])
        _vn = iip['virtual_network_refs']
        vn = _vn[0]
        vn.fetch()
        fqname = vn.fq_name
        subnet = self._get_subnet_for_ip(ip, self._get_subnet(vn))
        prefix = subnet.network
        prefix_len = subnet.prefixlen
        zk_req = self._zk_node_for_ip(
                    fqname,
                    prefix,
                    prefix_len,
                    ip
                    )
        logger.info('Creating zookeeper node {0} for IP {1}'
                    .format(str(zk_req), str(ip)))

        if not dry_run:
            try:
                self.zk_client.create(zk_req, value=str(iip.uuid))
                self.stats['miss_lock_fixed'] += 1
            except:
                self.stats['miss_lock_fix_failed'] += 1
                CommandError('Unable to create zookeeper znode for ip'
                             '{0} with path {1}'
                             .format(zk_req, ip))

    def add_znode_fip(self, ip, dry_run=True):
        fip = IPAddress(ip['floating_ip_address'])
        fip_pool = ip.parent
        fip_pool.fetch()
        vn = fip_pool.parent
        vn.fetch()
        fqname = vn.fq_name
        subnet = self._get_subnet_for_ip(fip, self._get_subnet(vn))
        prefix = subnet.network
        prefix_len = subnet.prefixlen
        zk_req = self._zk_node_for_ip(fqname, prefix, prefix_len, fip)
        logger.info('Creating zookeeper node {0} for IP {1}'
                    .format(str(zk_req), str(ip)))

        if not dry_run:
            try:
                self.zk_client.create(zk_req, value=str(ip.uuid))
                self.stats['miss_lock_fixed'] += 1
            except:
                self.stats['miss_lock_fix_failed'] += 1
                CommandError('Unable to create zookeeper znode for ip'
                             '{0} with path {1}'
                             .format(fip, zk_req))

    def add_znode_reserved_ip(self, _ip, vn, dry_run=True):
        ip = IPAddress(_ip)
        vn.fetch()
        fqname = vn.fq_name
        subnet = self._get_subnet_for_ip(ip, self._get_subnet(vn))
        prefix = subnet.network
        prefix_len = subnet.prefixlen
        zk_req = self._zk_node_for_ip(fqname, prefix, prefix_len, ip)
        if not self.dry_run:
            try:
                self.zk_client.create(zk_req, value=str(vn.uuid))
                self.stats['miss_lock_fixed'] += 1
            except:
                self.stats['miss_lock_fix_failed'] += 1
                CommandError('Unable to create zookeeper znode for ip'
                             '{0} with path {1}'
                             .format(ip, zk_req))

    def del_znode_ip(self, ip, zk_path, dry_run=True):
        logger.info("deleting zookeeper node {0} for IP {1}"
                    .format(int(IPAddress(ip)), str(IPAddress(ip))))
        if not self.dry_run:
            try:
                self.zk_client.delete(zk_path)
                self.stats['abusive_lock_fixed'] += 1
            except:
                self.stats['abusive_lock_fix_failed'] += 1
                CommandError('Unable to delete zookeeper znode for ip '
                             '{0} with path {1}'
                             .format(str(IPAddress(ip)), str(zk_path)))
        return

    def __call__(self, yes=False, **kwargs):
        super(FixZkIP, self).__call__(**kwargs)
        for r in self.resources:
            self.stats = {'miss_lock': 0,
                          'miss_lock_fixed': 0,
                          'miss_lock_fix_failed': 0,
                          'abusive_lock': 0,
                          'abusive_lock_fixed': 0,
                          'abusive_lock_fix_failed': 0,
                          'healthy_lock': 0}
            r.fetch()
            ips = {}
            if (not yes and
                    not self.dry_run and
                    not self.check and
                    not continue_prompt("Do you really want to repair " +
                                        str(r.fq_name) + " network?")):
                raise CommandError("Exiting.")

            if 'network_ipam_refs' in r:
                zk_ips = self.get_zk_ip(r)
                api_ips = self.get_api_ip(r)
            else:
                logger.info('No subnet found for network {0} '
                            .format(str(r.fq_name)))
                continue

            ips_index = set(api_ips.keys()) | set(zk_ips.keys())

            for ip in ips_index:
                zk_ok = False
                api_ok = False
                ips[ip] = {}
                try:
                    ips[ip].update({'zk_path': zk_ips[ip]})
                    logger.info(str(ip) + ' : ZOOKEEPER OK')
                    zk_ok = True
                except:
                    logger.info(str(ip) + ' : NOT FOUND IN ZOOKEEPER')
                    self.stats['miss_lock'] += 1
                    if not self.check:
                        self.add_znode_ip(ip,
                                          api_ips[ip],
                                          dry_run=self.dry_run)
                try:
                    ips[ip].update({'resource': api_ips[ip]})
                    logger.info(str(ip) + ' : API OK')
                    api_ok = True
                except:
                    logger.info(str(ip) + ' : NOT FOUND IN API')
                    self.stats['abusive_lock'] += 1
                    if not self.check:
                        self.del_znode_ip(ip, zk_ips[ip], dry_run=self.dry_run)

                if zk_ok and api_ok:
                    self.stats['healthy_lock'] += 1

            if (self.stats['miss_lock'] == 0 and
               self.stats['abusive_lock'] == 0):
                status = 'OK'
            else:
                status = 'KO'
            print('{0} : {1}'.format(str(r.fq_name), status))
            if status == 'KO':
                print('Healthy locks : {0} '
                      .format(str(self.stats['healthy_lock'])))
                print('Missing locks : {0} '
                      .format(str(self.stats['miss_lock'])))
                if not self. dry_run:
                    print('Fixed missing locks : {0}'
                          .format(str(self.stats['miss_lock_fixed'])))
                    print('Failed missing locks fix: {0}'
                          .format(str(self.stats['miss_lock_fix_failed'])))
                print('Abusive locks : {0} '
                      .format(str(self.stats['abusive_lock'])))
                if not self.dry_run:
                    print('Fixed abusive locks : {0} '
                          .format(str(self.stats['abusive_lock_fixed'])))
                    print('Failed abusive locks fix: {0} '
                          .format(str(self.stats['abusive_lock_fix_failed'])))
            print()
