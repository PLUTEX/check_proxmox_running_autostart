#!/usr/bin/python3

import argparse
import itertools
import sys
from enum import IntEnum
from collections import namedtuple

from proxmoxer import ProxmoxAPI


VM = namedtuple('VM', ['node', 'vmid', 'name', 'status', 'autostart'])
NagiosResult = namedtuple('NagiosResult', ['code', 'summary', 'details'])


class ResultCode(IntEnum):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3


def check_cluster(config):
    return generate_result(tuple(get_mismatched_vms(ProxmoxAPI(**config))))


def generate_result(mismatched_vms):
    return NagiosResult(
        ResultCode.WARNING if len(mismatched_vms) > 0 else ResultCode.OK,
        '{} VMs with mismatched running state and autostart setting.'.format(
            len(mismatched_vms),
        ),
        '\n'.join(
            '{name} on {node} is {status} but autostart={autostart}'.format(**vm._asdict())
            for vm in mismatched_vms
        )
    )


def get_mismatched_vms(pve):
    for node in pve.nodes.get():
        for vm in pve.nodes(node['node']).qemu.get():
            vm_config = pve.nodes(node['node']).qemu(vm['vmid']).config.get()
            onboot = vm_config.get('onboot', 0)
            if (vm['status'] == 'running') ^ (onboot == 1):
                yield VM(
                    node=node['node'],
                    vmid=vm['vmid'],
                    name=vm['name'],
                    status=vm['status'],
                    autostart=onboot,
                )


def check_all(config):
    mismatched_vms = tuple(itertools.chain.from_iterable(
        get_mismatched_vms(ProxmoxAPI(**config[section]))
        for section in config.sections()
    ))
    return generate_result(mismatched_vms)


def handle_result(result):
    print('{}: {}\n{}'.format(result[0].name, result[1], result[2]))
    sys.exit(result[0])


if __name__ == '__main__':
    import configparser

    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=argparse.FileType('r'))
    parser.add_argument('--section', help='Config section to use (default: all)')
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read_file(args.config)

    if args.section:
        handle_result(check_cluster(config[args.section]))
    else:
        handle_result(check_all(config))
