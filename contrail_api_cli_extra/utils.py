from six import text_type
import argparse
import netaddr


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


def ip_port_type(value):
    try:
        ip, port = value.split(':')
    except ValueError:
        raise argparse.ArgumentTypeError("IP and port must be separated by the ':' character")
    ip_type(ip)
    port_type(port)
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
