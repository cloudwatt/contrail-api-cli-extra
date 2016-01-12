from six import text_type
import argparse
import netaddr


def ip_type(string):
    try:
        return text_type(netaddr.IPAddress(string))
    except netaddr.core.AddrFormatError:
        raise argparse.ArgumentTypeError('%s is not an ip address' % string)
