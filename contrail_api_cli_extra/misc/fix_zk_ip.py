# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from netaddr import IPNetwork, IPAddress, AddrFormatError
from contrail_api_cli.command import Option
from contrail_api_cli.utils import continue_prompt
from contrail_api_cli.exceptions import(CommandError,
                                        ResourceNotFound)

import logging

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

    def _zk_node_for_ip(self, vn, ip):
        try:
            vn.fetch()
        except ResourceNotFound:
            raise ResourceNotFound('virtual-network {} not found.'
                                   .format(str(vn)))
            return
        try:
            subnets = self._get_subnet(vn)
        except CommandError:
            msg = ('No subnet found for virtual_network {0}'.format(str(vn)))
            logger.info(msg)
            print(msg)
            return
        try:
            ip_subnet = self._get_subnet_for_ip(ip, subnets)
        except ResourceNotFound:
            raise ResourceNotFound('No suitable subnet found for IP {0}'
                                   'in virtual_network {1}'
                                   .format(str(ip), str(vn)))
        return ('/api-server/subnets/{0}:{1}/{2}/{3}'
                .format(vn.fq_name,
                        ip_subnet.network,
                        ip_subnet.prefixlen,
                        int(ip)))

    def _get_subnet(self, virtual_network):
        subnet = []
        vn_subnet = (virtual_network['network_ipam_refs'][0]
                                    ['attr']['ipam_subnets'])
        for s in vn_subnet:
            prefix = s['subnet']['ip_prefix']
            prefix_len = s['subnet']['ip_prefix_len']
            subnet.append((IPNetwork(str(prefix) + '/' + str(prefix_len))))
        if subnet:
            return subnet
        else:
            raise ResourceNotFound('No subnet defined for virtual_network {0}'
                                   .format(str(virtual_network)))

    def _get_subnet_for_ip(self, ip, subnets):
        for subnet in subnets:
            if ip in subnet:
                return subnet
        raise CommandError('Subnet not found for IP {0} in subnet(s) {1}'
                           .format(str(ip), subnets))

    def get_zk_ip(self, virtual_network):
        zk_ips = {}
        try:
            virtual_network.fetch()
        except ResourceNotFound:
            return zk_ips
        fq_name = str(virtual_network.fq_name)
        if len(virtual_network['network_ipam_refs']
                              [0]['attr']['ipam_subnets']) == 0:
            msg = ('No subnet defined for {0}'.format(fq_name))
            logger.info(msg)
            print(msg)
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
                except AddrFormatError:
                    msg = ('{0} INVALID IP : zk_path={1}/{2}'
                           .format(str(_ip), zk_subnet_req, str(_ip)))
                    logger.warning(msg)
                    print(msg)
                    continue
                try:
                    self._get_subnet_for_ip(zk_ip, [s])
                except CommandError:
                    msg = ('{0} OUT OF RANGE {1} : zk_path={2}/{3}'
                           .format(str(zk_ip),
                                   str(s.cidr),
                                   zk_subnet_req,
                                   int(zk_ip)))
                    logger.warning(msg)
                    print(msg)
                    continue
                zk_ips[str(zk_ip)] = zk_subnet_req + '/' + str(_ip)
        return zk_ips

    def get_api_ip(self, vn):
        api_ips = {}
        try:
            vn.fetch()
        except ResourceNotFound:
            return api_ips
        if len(vn['network_ipam_refs'][0]['attr']['ipam_subnets']) == 0:
            msg = ('No subnet defined for {0}'.format(vn))
            logger.info(msg)
            print (msg)
            return api_ips
        vn_subnet = vn['network_ipam_refs'][0]['attr']['ipam_subnets']
        for s in vn_subnet:
            prefix = s['subnet']['ip_prefix']
            prefix_len = s['subnet']['ip_prefix_len']
            subnet = (IPNetwork(str(prefix) + '/' + str(prefix_len)))
            api_ips[str(subnet.network)] = vn
            api_ips[str(subnet.broadcast)] = vn
            # Some networks do have dns and gateway IPs
            if 'default_gateway' in s:
                api_ips[str(IPAddress(s['default_gateway']))] = vn
            if 'dns_server_address' in s:
                api_ips[str(IPAddress(
                        s['dns_server_address']))] = vn
        if 'instance_ip_back_refs' in vn:
            for iip in vn.back_refs.instance_ip:
                try:
                    iip.fetch()
                except ResourceNotFound:
                    continue
                try:
                    index = str(IPAddress(iip['instance_ip_address']))
                    api_ips[index] = iip
                except AddrFormatError:
                    msg = ('{0} for virtual network {1} is not a '
                           'valid IP address. unable to check it.'
                           .format(index, vn.fq_name))
                    logger.info(msg)
                    print(msg)

        if 'floating_ip_pools' in vn:
            logger.debug(str(vn.fq_name) + " is a public network")
            for pool in vn.children.floating_ip_pool:
                try:
                    pool.fetch()
                except ResourceNotFound:
                    continue
                for fip in pool.children.floating_ip:
                    try:
                        fip.fetch()
                    except ResourceNotFound:
                        continue
                    try:
                        index = str(IPAddress(fip['floating_ip_address']))
                        api_ips[index] = fip
                    except AddrFormatError:
                        msg = ('{0} for virtual network {1} is not a '
                               'valid IP address. unable to check it.'
                               .format(index, vn.fq_name))
                        logger.info(msg)
                        print(msg)
                        continue
                    api_ips[index] = fip
        return api_ips

    def create_znode(self, zk_req, data, dry_run=True):
        if self.zk_client.exists(str(zk_req)):
            msg = ('{0} allready exists'.format(zk_req))
            logger.info(msg)
            print(msg)
            self.stats['miss_lock_fixed'] += 1
            return
        if not dry_run:
            try:
                self.zk_client.create(zk_req,
                                      value=str(data),
                                      makepath=True)
                self.stats['miss_lock_fixed'] += 1
            except:
                self.stats['miss_lock_fix_failed'] += 1
                msg = ('Unable to create zookeeper znode {0}'
                       .format(zk_req,))
                CommandError(msg)

    def del_znode_ip(self, ip, zk_path, dry_run=True):
            msg = ("deleting zookeeper node {0} for IP {1}"
                   .format(int(IPAddress(ip)), str(IPAddress(ip))))
            logger.info(msg)
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

    def add_ip_lock(self, vn, ip, data_lock, dry_run):
        if not IPAddress(ip):
            raise CommandError('Invalid IP {0}'.format(ip))
            return
        try:
            vn.fetch()
        except ResourceNotFound:
            return
        zk_req = self._zk_node_for_ip(vn, ip)
        logger.info('Creating zookeeper node {0} for IP {1}'
                    .format(str(zk_req), str(ip)))
        if not dry_run:
            self.create_znode(zk_req, data_lock, dry_run)

    def add_znode_ip(self, _ip, resource, dry_run=True):
        try:
            resource.fetch()
        except ResourceNotFound:
            return
        try:
            ip = IPAddress(_ip)
        except AddrFormatError:
            return
        if resource.type == 'floating-ip':
            fip_pool = resource.parent
            try:
                fip_pool.fetch()
            except ResourceNotFound:
                return
            try:
                vn = fip_pool.parent
                vn.fetch()
            except ResourceNotFound:
                return
            data = resource.uuid
        elif resource.type == 'instance-ip':
            try:
                vn = resource['virtual_network_refs'][0]
                vn.fetch()
            except ResourceNotFound:
                return
            data = vn.uuid
        elif resource.type == 'virtual-network':
            try:
                vn = resource
                vn.fetch()
            except ResourceNotFound:
                return
            data = vn.uuid
        else:
            print('Unknow type for ip {0}'.format(ip))
            return
        self.add_ip_lock(vn, ip, data, dry_run)

    def check_tupple(self, api_ips, zk_ips):
        ips = {}
        ips_index = set(api_ips.keys()) | set(zk_ips.keys())

        for ip in ips_index:
            zk_ok = False
            api_ok = False
            ips[ip] = {}
            if ip in zk_ips:
                ips[ip].update({'zk_path': zk_ips[ip]})
                logger.info(str(ip) + ' : ZOOKEEPER OK')
                zk_ok = True
            else:
                logger.info(str(ip) + ' : NOT FOUND IN ZOOKEEPER')
                self.stats['miss_lock'] += 1
                if not self.check:
                    self.add_znode_ip(ip,
                                      api_ips[ip],
                                      dry_run=self.dry_run)
            if ip in api_ips:
                ips[ip].update({'resource': api_ips[ip]})
                logger.info(str(ip) + ' : API OK')
                api_ok = True
            else:
                logger.info(str(ip) + ' : NOT FOUND IN API')
                self.stats['abusive_lock'] += 1
                if not self.check:
                    self.del_znode_ip(ip, zk_ips[ip], dry_run=self.dry_run)
            if zk_ok and api_ok:
                self.stats['healthy_lock'] += 1
        return

    def print_stats(self, resource):
        if (self.stats['miss_lock'] == 0 and
           self.stats['abusive_lock'] == 0):
            status = 'OK'
        else:
            status = 'KO'
        print('{0} : {1}'.format(str(resource.fq_name), status))
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
            if (not yes and
                    not self.dry_run and
                    not self.check and
                    not continue_prompt("Do you really want to repair " +
                                        str(r.fq_name) + " network?")):
                raise CommandError("Exiting.")
            try:
                r.fetch()
            except ResourceNotFound:
                continue
            if 'network_ipam_refs' in r:
                zk_ips = self.get_zk_ip(r)
                api_ips = self.get_api_ip(r)
            else:
                logger.info('No subnet found for network {0} '
                            .format(str(r.fq_name)))
                continue
            self.check_tupple(api_ips, zk_ips)
            self.print_stats(r)
