import sys
from setuptools import setup, find_packages

install_requires = [
    'contrail-api-cli>=0.1',
    'pycassa',
    'kazoo',
    'networkx',
    'pydotplus',
    'python-novaclient',
    'PrettyTable'
]
test_requires = []

if sys.version_info[0] == 2:
    test_requires.append('mock')


setup(
    name='contrail-api-cli-extra',
    version='0.3',
    description="Supplementary commands for contrail-api-cli",
    author="Jean-Philippe Braun",
    author_email="jean-philippe.braun@cloudwatt.com",
    maintainer="Jean-Philippe Braun",
    maintainer_email="jean-philippe.braun@cloudwatt.com",
    url="http://www.github.com/cloudwatt/contrail-api-cli-extra",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    scripts=[],
    license="MIT",
    entry_points={
        'contrail_api_cli.provision': [
            'add-sas = contrail_api_cli_extra.provision.service_appliance_set:AddSAS',
            'del-sas = contrail_api_cli_extra.provision.service_appliance_set:DelSAS',
            'list-sas = contrail_api_cli_extra.provision.service_appliance_set:ListSAS',
            'set-global-asn = contrail_api_cli_extra.provision.global_asn:SetGlobalASN',
            'get-global-asn = contrail_api_cli_extra.provision.global_asn:GetGlobalASN',
            'add-dns-nameserver = contrail_api_cli_extra.provision.dns_nameserver:AddDNSNameserver',
            'del-dns-nameserver = contrail_api_cli_extra.provision.dns_nameserver:DelDNSNameserver',
            'list-dns-nameserver = contrail_api_cli_extra.provision.dns_nameserver:ListDNSNameserver',
            'add-bgp-router = contrail_api_cli_extra.provision.bgp_router:AddBGPRouter',
            'del-bgp-router = contrail_api_cli_extra.provision.bgp_router:DelBGPRouter',
            'list-bgp-router = contrail_api_cli_extra.provision.bgp_router:ListBGPRouter',
            'add-linklocal = contrail_api_cli_extra.provision.linklocal:AddLinklocal',
            'del-linklocal = contrail_api_cli_extra.provision.linklocal:DelLinklocal',
            'list-linklocal = contrail_api_cli_extra.provision.linklocal:ListLinklocal',
            'set-route-targets = contrail_api_cli_extra.provision.route_target:SetRouteTargets',
            'get-route-targets = contrail_api_cli_extra.provision.route_target:GetRouteTargets',
            'set-encaps = contrail_api_cli_extra.provision.encapsulation:SetEncapsulation',
            'get-encaps = contrail_api_cli_extra.provision.encapsulation:GetEncapsulation',
            'add-vrouter = contrail_api_cli_extra.provision.vrouter:AddVRouter',
            'del-vrouter = contrail_api_cli_extra.provision.vrouter:DelVRouter',
            'list-vrouter = contrail_api_cli_extra.provision.vrouter:ListVRouter',
            'add-config = contrail_api_cli_extra.provision.config:AddConfig',
            'del-config = contrail_api_cli_extra.provision.config:DelConfig',
            'list-config = contrail_api_cli_extra.provision.config:ListConfig',
            'add-analytics = contrail_api_cli_extra.provision.analytics:AddAnalytics',
            'del-analytics = contrail_api_cli_extra.provision.analytics:DelAnalytics',
            'list-analytics = contrail_api_cli_extra.provision.analytics:ListAnalytics',
            'add-vn = contrail_api_cli_extra.provision.vn:AddVN',
            'del-vn = contrail_api_cli_extra.provision.vn:DelVN',
            'list-vn = contrail_api_cli_extra.provision.vn:ListVNs',
            'set-subnets = contrail_api_cli_extra.provision.subnet:SetSubnets',
            'get-subnets = contrail_api_cli_extra.provision.subnet:GetSubnets',
        ],
        'contrail_api_cli.command': [
            'provision = contrail_api_cli_extra.provision.provision:Provision',
            'rpf = contrail_api_cli_extra.misc.rpf:RPF',
            'dot = contrail_api_cli_extra.misc.dot:Dot',
            'find-orphaned-projects = contrail_api_cli_extra.clean.project:FindOrphanedProjects',
            'reschedule-vm = contrail_api_cli_extra.misc.vm:RescheduleVM',
            'fix-vn-id = contrail_api_cli_extra.fix.fix_vn_id:FixVnId',
            'fix-sg = contrail_api_cli_extra.fix.fix_sg:FixSg',
            'fix-fip-locks = contrail_api_cli_extra.fix.fix_fip_locks:FixFIPLocks',
            'fix-subnets = contrail_api_cli_extra.fix.fix_subnets:FixSubnets',
            'fix-zk-ip = contrail_api_cli_extra.fix.fix_zk_ip:FixZkIP',
        ],
        'contrail_api_cli.migration': [
            'migrate-si = contrail_api_cli_extra.migration.si:MigrateSI110221',
            'migrate-host-routes = contrail_api_cli_extra.migration.host_routes:MigrateHostRoutes',
        ],
        'contrail_api_cli.clean': [
            'purge-project = contrail_api_cli_extra.clean.project:PurgeProject',
            'clean-orphaned-acl = contrail_api_cli_extra.clean.orphaned_acl:OrphanedACL',
            'clean-stale-si = contrail_api_cli_extra.clean.si:CleanStaleSI',
            'clean-route-target = contrail_api_cli_extra.clean.rt:CleanRT',
            'clean-si-scheduling = contrail_api_cli_extra.clean.si:CleanSIScheduling',
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
