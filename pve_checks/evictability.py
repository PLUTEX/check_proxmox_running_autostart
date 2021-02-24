from collections import defaultdict
from math import log2

from proxmoxer import ProxmoxAPI

from . import call_function
from .nagios import ResultCode, NagiosResult


# Source: https://stackoverflow.com/a/65106281/9183748
# CC BY-SA 4.0 ErikW (134975037440)
def datasize(size):
    """
    Calculate the size of a code in B/KB/MB.../
    Return a tuple of (value, unit)
    """
    assert size > 0, "Size must be a positive number"
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB",  "EiB", "ZiB", "YiB")
    scaling = round(log2(size)*4)//40
    scaling = min(len(units)-1, scaling)
    return "%.1f %s" % (size/(2**(10*scaling)), units[scaling])


def check(pve: ProxmoxAPI = None):
    if not pve:
        # we need to make the argument itself optional for argh
        raise RuntimeError('pve parameter missing')

    resources = pve.cluster.resources.get()
    stats = defaultdict(lambda: {
        'used': {
            'actual': 0,
            'theoretical': 0,
        },
        'free': {}
    })
    for resource in resources:
        node_stats = stats[resource['node']]
        if resource['type'] == 'node':
            node_stats['node'] = resource['node']
            node_stats['free']['theoretical'] = resource['maxmem']
            node_stats['free']['actual'] = resource['maxmem'] - resource['mem']
        elif resource['type'] == 'qemu':
            node_stats['used']['actual'] += resource['mem']
            node_stats['used']['theoretical'] += resource['maxmem']

    for node_stats in stats.values():
        node_stats['free']['theoretical'] -= node_stats['used']['theoretical']

    for variant in ('actual', 'theoretical'):
        biggest = max(stats.values(), key=lambda x: x['used'][variant])
        free_other = sum(
            x['free'][variant]
            for x in stats.values()
            if x['node'] != biggest['node']
        )

        if biggest['used'][variant] > free_other:
            yield NagiosResult(
                code=(
                    ResultCode.CRITICAL
                    if variant == 'actual'
                    else ResultCode.WARNING
                ),
                summary='Eviction of biggest node impossible',
                details=(
                    '{node}\'s {variant} usage is {used}, '
                    'but {variant} free RAM on other hosts '
                    'is only {free_other}'
                ).format(
                    node=biggest['node'],
                    variant=variant,
                    used=datasize(biggest['used'][variant]),
                    free_other=datasize(free_other),
                )
            )
            break


def main():
    call_function(check)


if __name__ == '__main__':
    main()
