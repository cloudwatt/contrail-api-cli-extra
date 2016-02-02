import sys
from setuptools import setup, find_packages

install_requires = [
    #'contrail-api-cli>=0.1b1'
    'pycassa',
]
test_requires = []

if sys.version_info[0] == 2:
    test_requires.append('mock')


setup(
    name='contrail-api-cli-extra',
    version='0.2b1',
    description="Supplementary commands for contrail-api-cli",
    author="Jean-Philippe Braun",
    author_email="eon@patapon.info",
    maintainer="Jean-Philippe Braun",
    maintainer_email="eon@patapon.info",
    url="http://www.github.com/eonpatapon/contrail-api-cli-extra",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    scripts=[],
    license="MIT",
    entry_points={
        'contrail_api_cli.provision': [
            'add-sas = contrail_api_cli_extra.service_appliance_set:AddSAS',
            'del-sas = contrail_api_cli_extra.service_appliance_set:DelSAS',
            'list-sas = contrail_api_cli_extra.service_appliance_set:ListSAS',
            'set-global-asn = contrail_api_cli_extra.global_asn:SetGlobalASN',
            'get-global-asn = contrail_api_cli_extra.global_asn:GetGlobalASN',
            'add-dns-nameserver = contrail_api_cli_extra.dns_nameserver:AddDNSNameserver',
            'del-dns-nameserver = contrail_api_cli_extra.dns_nameserver:DelDNSNameserver',
            'list-dns-nameserver = contrail_api_cli_extra.dns_nameserver:ListDNSNameserver',
            'add-bgp-router = contrail_api_cli_extra.bgp_router:AddBGPRouter',
            'del-bgp-router = contrail_api_cli_extra.bgp_router:DelBGPRouter',
            'list-bgp-router = contrail_api_cli_extra.bgp_router:ListBGPRouter',
            'add-linklocal = contrail_api_cli_extra.linklocal:AddLinklocal',
            'del-linklocal = contrail_api_cli_extra.linklocal:DelLinklocal',
            'list-linklocal = contrail_api_cli_extra.linklocal:ListLinklocal',
            'set-route-targets = contrail_api_cli_extra.route_target:SetRouteTargets',
            'get-route-targets = contrail_api_cli_extra.route_target:GetRouteTargets',
            'set-encaps = contrail_api_cli_extra.encapsulation:SetEncapsulation',
            'get-encaps = contrail_api_cli_extra.encapsulation:GetEncapsulation',
            'add-vrouter = contrail_api_cli_extra.vrouter:AddVRouter',
            'del-vrouter = contrail_api_cli_extra.vrouter:DelVRouter',
            'list-vrouter = contrail_api_cli_extra.vrouter:ListVRouter',
            'add-config = contrail_api_cli_extra.config:AddConfig',
            'del-config = contrail_api_cli_extra.config:DelConfig',
            'list-config = contrail_api_cli_extra.config:ListConfig',
            'add-analytics = contrail_api_cli_extra.analytics:AddAnalytics',
            'del-analytics = contrail_api_cli_extra.analytics:DelAnalytics',
            'list-analytics = contrail_api_cli_extra.analytics:ListAnalytics',
            'add-vn = contrail_api_cli_extra.vn:AddVN',
            'del-vn = contrail_api_cli_extra.vn:DelVN',
            'list-vn = contrail_api_cli_extra.vn:ListVNs',
            'set-subnets = contrail_api_cli_extra.subnet:SetSubnets',
            'get-subnets = contrail_api_cli_extra.subnet:GetSubnets',
        ],
        'contrail_api_cli.command': [
            'provision = contrail_api_cli_extra.provision:Provision',
            'clean-orphaned-acl = contrail_api_cli_extra.cleaner.orphaned_acl:OrphanedACL',
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: User Interfaces',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4'
    ],
    tests_require=test_requires,
    test_suite="tests"
)
