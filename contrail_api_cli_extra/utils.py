# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six import text_type
import argparse
import netaddr
import re
import abc
from six import add_metaclass

from kazoo.client import KazooClient
from kazoo.handlers.gevent import SequentialGeventHandler

from contrail_api_cli.command import Command, Arg, Option, expand_paths
from contrail_api_cli.exceptions import CommandError
from contrail_api_cli.resource import Collection


def ip_type(string):
    try:
        return text_type(netaddr.IPAddress(string))
    except netaddr.AddrFormatError:
        raise argparse.ArgumentTypeError('%s is not an ip address' % string)


def network_type(string):
    try:
        return text_type(netaddr.IPNetwork(string))
    except netaddr.AddrFormatError:
        raise argparse.ArgumentTypeError('%s is not a network' % string)


def port_type(value):
    try:
        value = int(value)
        if not 1 <= value <= 65535:
            raise argparse.ArgumentTypeError("Port number must be contained between 1 and 65535")
        return value
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def server_type(value):
    server = value.split(':')
    if len(server) > 2:
        raise argparse.ArgumentTypeError("Server can be composed to the hostname and port separated by the ':' character")
    if len(server) == 2:
        port = server[1]
        port_type(port)
    return value


def md5_type(value):
    if value and not re.match(r"([a-fA-F\d]{32})", value):
        raise argparse.ArgumentTypeError("MD5 hash %s is not valid" % value)
    return value


class RouteTargetAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        unique_values = set(values)
        ret_values = []
        for value in unique_values:
            ret_values.append(RouteTargetAction.route_target_type(value))
        setattr(namespace, self.dest, ret_values)

    @staticmethod
    def asn_type(value):
        try:
            value = int(value)
            if not 1 <= value <= 65534:
                raise argparse.ArgumentTypeError("AS number must be contained between 1 and 65534")
            return value
        except ValueError:
            pass
        try:
            return text_type(netaddr.IPNetwork(value, version=4).ip)
        except netaddr.AddrFormatError as e:
            raise argparse.ArgumentTypeError(str(e))

    @staticmethod
    def route_target_type(value):
        try:
            asn, rt_num = value.split(':')
        except ValueError:
            raise argparse.ArgumentTypeError("A router target must be composed by an ASN and a number separated by the ':' character")

        asn = RouteTargetAction.asn_type(asn)

        try:
            rt_num = int(rt_num)
        except ValueError:
            raise argparse.ArgumentTypeError("Route target number must be an integer")
        if isinstance(asn, int) and not 1 <= rt_num < pow(2, 32):
            raise argparse.ArgumentTypeError("With ASN as integer, the route target number must be contained between 1 and %d" % pow(2, 32))
        elif isinstance(asn, unicode) and not 1 <= rt_num < pow(2, 16):
            raise argparse.ArgumentTypeError("With ASN as IPv4, the route target number must be contained between 1 and %d" % pow(2, 16))

        return 'target:%s' % value


class ZKCommand(Command):
    zk_server = Option(help="zookeeper server (default: %(default)s)",
                       type=server_type,
                       default='localhost:2181')

    def __call__(self, zk_server=None, **kwargs):
        handler = SequentialGeventHandler()
        self.zk_client = KazooClient(hosts=zk_server, timeout=1.0,
                                     handler=handler)
        try:
            self.zk_client.start()
        except handler.timeout_exception:
            raise CommandError("Can't connect to Zookeeper at %s" % zk_server)

        super(ZKCommand, self).__call__(**kwargs)


class CheckCommand(Command):
    check = Option('-c',
                   default=False,
                   action="store_true")
    dry_run = Option('-n',
                     default=False,
                     action="store_true",
                     help='run this command in dry-run mode')

    def __call__(self, dry_run=None, check=None, **kwargs):
        self.dry_run = dry_run
        self.check = check
        super(CheckCommand, self).__call__(**kwargs)


@add_metaclass(abc.ABCMeta)
class PathCommand(Command):

    @abc.abstractproperty
    def resource_type(self):
        """Type of resource the command
        is about.
        """
        return "resource_type"

    def __new__(cls, *args):
        cmd = super(PathCommand, cls).__new__(cls, *args)
        cls.paths = Arg(nargs="*",
                        help="{type} path(s). "
                             "When no path is provided "
                             "all {type}s are considered.".format(type=cmd.resource_type),
                        metavar='path',
                        complete="resources:%s:path" % cmd.resource_type)
        return cmd

    def __call__(self, paths=None, **kwargs):
        if not paths:
            self.resources = Collection(self.resource_type, fetch=True)
        else:
            self.resources = expand_paths(paths,
                                          predicate=lambda r: r.type == self.resource_type)
        super(PathCommand, self).__call__(**kwargs)
