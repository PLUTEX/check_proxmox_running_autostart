from datetime import datetime, timedelta
from typing import Iterable

import argh
from proxmoxer import ProxmoxAPI

from . import call_function
from .nagios import ResultCode, NagiosResult


@argh.arg('--age', help='maximum age in days of backup tasks to consider')
def check(pve: ProxmoxAPI = None, age: int = 7) -> Iterable[NagiosResult]:
    if not pve:
        # we need to make the argument itself optional for argh
        raise RuntimeError('pve parameter missing')

    cutoff = int((datetime.now() - timedelta(days=age)).timestamp())

    for node in pve.nodes.get():
        last_failed = 0
        last_success = 0
        for task in pve.nodes(node['node']).tasks.get(typefilter='vzdump'):
            if task['endtime'] < cutoff:
                continue

            if task['status'] == 'OK':
                last_success = max(last_success, task['endtime'])
            else:
                last_failed = max(last_failed, task['endtime'])

        if last_failed > last_success:
            yield NagiosResult(
                ResultCode.CRITICAL,
                '',  # unused at this stage
                'Last backup of node {} at {} had errors'.format(
                    node['node'],
                    datetime.fromtimestamp(last_failed),
                ),
            )
        elif not last_success:
            yield NagiosResult(
                ResultCode.WARNING,
                '',  # unused at this stage
                'Last backup of node {} older than cutoff'.format(
                    node['node'],
                ),
            )
        else:
            yield NagiosResult(
                ResultCode.OK,
                '',  # unused at this stage
                'Last backup of node {} at {} was successful'.format(
                    node['node'],
                    datetime.fromtimestamp(last_success),
                ),
            )


def main():
    call_function(check)


if __name__ == '__main__':
    main()
