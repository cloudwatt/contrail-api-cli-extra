import sys
from setuptools import setup, find_packages

install_requires = [
    #'contrail-api-cli>=0.1b1'
]
test_requires = []

if sys.version_info[0] == 2:
    test_requires.append('mock')


setup(
    name='contrail-api-cli-extra',
    version='0.1',
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
        'contrail_api_cli.command': [
            'hello = contrail_api_cli_extra.hello:Hello',
            'add-sas = contrail_api_cli_extra.service_appliance_set:AddSAS',
            'set-global-asn = contrail_api_cli_extra.global_asn:SetGlobalASN',
            'dns-nameserver = contrail_api_cli_extra.dns_nameserver:DnsNameserver',
            'add-bgp-router = contrail_api_cli_extra.bgp_router:AddBGPRouter',
            'del-bgp-router = contrail_api_cli_extra.bgp_router:DelBGPRouter',
            'linklocal = contrail_api_cli_extra.linklocal:Linklocal',
            'route-target = contrail_api_cli_extra.route_target:RouteTarget',
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
