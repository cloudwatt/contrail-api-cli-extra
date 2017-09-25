# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from six import text_type
import logging
from collections import namedtuple

import kazoo
from netaddr import IPNetwork, IPAddress, AddrFormatError

from contrail_api_cli.exceptions import CommandError, ResourceNotFound
from contrail_api_cli.utils import printo

from ..utils import ZKCommand, CheckCommand, PathCommand, ConfirmCommand


logger = logging.getLogger(__name__)
Subnet = namedtuple('Subnet', ['cidr', 'gateway', 'dns'])


class SubnetNotFound(Exception):
    pass

class ZkNodeNotFound(Exception):
    def __init__(self, zk_subnets):
        self.zk_subnets = zk_subnets

    def __str__(self):
        output = ["Node {0} do not exist in Zookeeper".format(str(subnet)) for subnet in self.zk_subnets]
        return "\n".join(output)

class UnhandledResourceType(Exception):
    pass


class FixZkIP(ZKCommand, CheckCommand, PathCommand, ConfirmCommand):
    """Remove or add ZK locks based on the IPAM configuration.

    Sometimes, when an instance-ip or a floating-ip is created or deleted, its
    associated zookeeper node isn't managed properly.

    This led to situation where, no IPs are reserved from the Contrail API
    standpoint and nevertheless, you are not able to get one, or the same
    floating IP address is reserved for several users/tenants.

    This command list all zookeeper nodes for a given network (which may
    contain one or several subnet) and compare the nodes with the IPs found
    with the contrail API. For each IP found in zookeeper and not in
    the contrail API (abusive lock scenario), the command delete the
    associated zookeeper node. Then, for each IP found in API, and not in Zookeeper,
    the command creates the appropriate lock.

    Usage::

        contrail-api-cli fix-zk-ip --zk-server <IP> [path/to/virtual-network] [--dry-run]

    If no virtual-network is given, all virtual-networks are considered.
    """
    description = "Remove or add ZK locks based on the IPAM configuration"

    @property
    def resource_type(self):
        return "virtual-network"

    @property
    def confirm_message(self):
        return 'Do you really want to repair networks ?'

    def _zk_node_for_subnet(self, fqname, subnet):
        return ('/api-server/subnets/%s:%s/%s' %
                (fqname, subnet.cidr.network, subnet.cidr.prefixlen))

    def _zk_node_for_ip(self, vn, ip):
        logger.debug("check IP {0} in virtual network {1}"
                     .format(ip, vn))
        subnets = self._get_vn_subnets(vn)
        ip_subnet = self._get_ip_subnet(subnets, ip)
        return ('/api-server/subnets/{0}:{1}/{2}/{3}'
                .format(vn.fq_name,
                        ip_subnet.cidr.network,
                        ip_subnet.cidr.prefixlen,
                        int(ip)))

    def _get_vn_subnets(self, vn):
        if not vn.refs.network_ipam:
            raise SubnetNotFound()

        subnets = []
        for ipam in vn.refs.network_ipam:
            ipam_subnets = ipam['attr']['ipam_subnets']
            for s in ipam_subnets:
                prefix = s['subnet']['ip_prefix']
                prefix_len = s['subnet']['ip_prefix_len']
                cidr = IPNetwork('%s/%s' % (prefix, prefix_len))
                gateway = dns = None
                if 'default_gateway' in s and s['default_gateway'] != '0.0.0.0':
                    gateway = IPAddress(s['default_gateway'])
                if 'dns_server_address' in s:
                    dns = IPAddress(s['dns_server_address'])
                subnets.append(Subnet(cidr, gateway, dns))

        if not subnets:
            raise SubnetNotFound()
        return subnets

    def _get_ip_subnet(self, subnets, ip):
        for s in subnets:
            if ip in s.cidr:
                return s
        raise SubnetNotFound('No subnet found for IP %s' % ip)

    def get_zk_ip(self, vn):
        zk_ips = {}
        subnets = self._get_vn_subnets(vn)
        zk_subnets_err = []

        for s in subnets:
            zk_subnet_req = self._zk_node_for_subnet(vn.fq_name, s)
            try:
                children = self.zk_client.get_children(zk_subnet_req)
            except kazoo.exceptions.NoNodeError:
                zk_subnets_err.append(zk_subnet_req)
                continue
            for ip in children:
                try:
                    zk_ip = IPAddress(int(ip))
                except AddrFormatError:
                    msg = ('{0} INVALID IP : zk_path={1}/{2}'
                           .format(text_type(ip), zk_subnet_req, text_type(ip)))
                    logger.warning(msg)
                    printo(msg)
                    continue
                try:
                    self._get_ip_subnet([s], zk_ip)
                except SubnetNotFound:
                    msg = ('{0} OUT OF RANGE {1} : zk_path={2}/{3}'
                           .format(text_type(zk_ip),
                                   text_type(s.cidr),
                                   zk_subnet_req,
                                   int(zk_ip)))
                    logger.warning(msg)
                    printo(msg)
                    continue
                zk_ips[zk_ip] = zk_subnet_req + '/' + text_type(int(zk_ip)).zfill(10)
        if zk_subnets_err:
            raise ZkNodeNotFound(zk_subnets_err)
        return zk_ips

    def get_api_ip(self, vn):
        api_ips = {}
        subnets = self._get_vn_subnets(vn)

        for subnet in subnets:
            api_ips[subnet.cidr.network] = vn
            api_ips[subnet.cidr.broadcast] = vn
            # Some networks do have dns and gateway IPs
            if subnet.gateway is not None:
                api_ips[subnet.gateway] = vn
            if subnet.dns is not None:
                api_ips[subnet.dns] = vn

        for iip in vn.back_refs.instance_ip:
            try:
                iip.fetch()
            except ResourceNotFound:
                continue
            try:
                iip_ip = IPAddress(iip['instance_ip_address'])
                api_ips[iip_ip] = iip
            except AddrFormatError:
                msg = ('{0} for virtual network {1} is not a '
                       'valid IP address. unable to check it.'
                       .format(iip_ip, vn.fq_name))
                logger.info(msg)
                printo(msg)

        for pool in vn.children.floating_ip_pool:
            try:
                pool.fetch()
                logger.debug(text_type(vn.fq_name) + " is a public network")
            except ResourceNotFound:
                continue
            for fip in pool.children.floating_ip:
                try:
                    fip.fetch()
                except ResourceNotFound:
                    continue
                try:
                    fip_ip = IPAddress(fip['floating_ip_address'])
                    api_ips[fip_ip] = fip
                except AddrFormatError:
                    msg = ('{0} for virtual network {1} is not a '
                           'valid IP address. unable to check it.'
                           .format(fip_ip, vn.fq_name))
                    logger.info(msg)
                    printo(msg)
                    continue

        return api_ips

    def create_znode(self, zk_req, data):
        if self.zk_client.exists(text_type(zk_req)):
            msg = ('{0} already exists'.format(zk_req))
            logger.info(msg)
            printo(msg)
            self.stats['miss_lock_fixed'] += 1
            return
        if not self.dry_run:
            try:
                # FIXME: python3
                self.zk_client.create(zk_req,
                                      value=str(data),
                                      makepath=True)
                self.stats['miss_lock_fixed'] += 1
            except:
                self.stats['miss_lock_fix_failed'] += 1
                msg = ('Unable to create zookeeper znode {0}'
                       .format(zk_req,))
                logger.exception(msg)
                raise CommandError(msg)

    def del_znode_ip(self, ip, zk_path):
        msg = ("Deleting zookeeper node %d for IP %s" % (int(ip), ip))
        printo(msg)
        if not self.dry_run:
            try:
                self.zk_client.delete(zk_path)
                self.stats['abusive_lock_fixed'] += 1
            except:
                self.stats['abusive_lock_fix_failed'] += 1
                printo('Unable to delete zookeeper znode for ip '
                      '%s with path %s' % (ip, zk_path))

    def add_ip_lock(self, vn, ip, data_lock):
        try:
            zk_req = self._zk_node_for_ip(vn, ip)
        except SubnetNotFound:
            self.stats['miss_lock_fix_failed'] += 1
            return
        msg = ('Creating zookeeper node %s for IP %s' % (zk_req, ip))
        printo(msg)
        if not self.dry_run:
            self.create_znode(zk_req, data_lock)

    def add_znode_ip(self, ip, resource):
        resource.fetch()
        vn = None

        if resource.type == 'floating-ip':
            fip_pool = resource.parent
            fip_pool.fetch()
            vn = fip_pool.parent
            vn.fetch()
        elif resource.type == 'instance-ip':
            vn = resource['virtual_network_refs'][0]
            vn.fetch()
        elif resource.type == 'virtual-network':
            vn = resource
        else:
            raise UnhandledResourceType('Unknow type for IP %s' % ip)

        assert vn is not None
        data_lock = vn.uuid
        self.add_ip_lock(vn, ip, data_lock)

    def check_tuple(self, api_ips, zk_ips):
        ips = {}
        ips_index = set(api_ips.keys()) | set(zk_ips.keys())

        for ip in ips_index:
            zk_ok = False
            api_ok = False
            ips[ip] = {}

            if ip in zk_ips:
                ips[ip].update({'zk_path': zk_ips[ip]})
                msg = (text_type(ip) + ' : ZOOKEEPER OK')
                logger.info(msg)
                zk_ok = True
            else:
                logger.info(text_type(ip) + ' : NOT FOUND IN ZOOKEEPER')
                self.stats['miss_lock'] += 1
                if not self.check:
                    try:
                        self.add_znode_ip(ip, api_ips[ip])
                    except (ResourceNotFound, UnhandledResourceType) as e:
                        msg = e.msg
                        logger.warning(e)
                        printo(msg)

            if ip in api_ips:
                ips[ip].update({'resource': api_ips[ip]})
                logger.info(text_type(ip) + ' : API OK')
                api_ok = True
            else:
                logger.info(text_type(ip) + ' : NOT FOUND IN API')
                self.stats['abusive_lock'] += 1
                if not self.check:
                    self.del_znode_ip(ip, zk_ips[ip])

            if zk_ok and api_ok:
                self.stats['healthy_lock'] += 1
        return

    def print_stats(self, resource):
        if (self.stats['miss_lock'] == 0 and
                self.stats['abusive_lock'] == 0):
            status = 'OK'
        else:
            status = 'KO'
        printo('Status : %s' % status)
        if status == 'KO':
            printo('Healthy locks : %d ' % self.stats['healthy_lock'])
            printo('Missing locks : %d ' % self.stats['miss_lock'])
            if not self. dry_run:
                printo('Fixed missing locks : %d' %
                       self.stats['miss_lock_fixed'])
                printo('Failed missing locks fix: %d' %
                       self.stats['miss_lock_fix_failed'])
            printo('Abusive locks : %d' % self.stats['abusive_lock'])
            if not self.dry_run:
                printo('Fixed abusive locks : %d' %
                       self.stats['abusive_lock_fixed'])
                printo('Failed abusive locks fix: %d' %
                       self.stats['abusive_lock_fix_failed'])
        printo("")

    def __call__(self, **kwargs):
        super(FixZkIP, self).__call__(**kwargs)
        for r in self.resources:
            self.stats = {'miss_lock': 0,
                          'miss_lock_fixed': 0,
                          'miss_lock_fix_failed': 0,
                          'abusive_lock': 0,
                          'abusive_lock_fixed': 0,
                          'abusive_lock_fix_failed': 0,
                          'healthy_lock': 0}
            try:
                r.fetch()
            except ResourceNotFound:
                continue
            printo("Checking VN %s" % r.fq_name)
            try:
                api_ips = self.get_api_ip(r)
                zk_ips = self.get_zk_ip(r)
                self.check_tuple(api_ips, zk_ips)
                self.print_stats(r)
            except SubnetNotFound:
                printo("No subnets found")
                printo("")
            except ZkNodeNotFound as exc:
                msg = str(exc)
                printo(msg)
