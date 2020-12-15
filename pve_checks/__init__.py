import argparse
import itertools
from typing import Callable

import argh
from proxmoxer import ProxmoxAPI

from .nagios import handle_result, merge_results


def call_function(f: Callable):
    parser = argh.helpers.ArghParser()
    parser.add_argument(
        'config_file',
        type=argparse.FileType('r'),
        help='path to config file with PVE credentials',
    )
    parser.add_argument(
        '--section',
        help='config section to use',
        action='append',
    )
    parser.set_default_command(argh.arg(
        '--pve',
        help=argparse.SUPPRESS,
        default=argparse.SUPPRESS,
    )(f))
    args = parser.parse_args()
    var_args = dict(vars(args))
    del var_args['config_file']
    del var_args['section']
    del var_args['_functions_stack']

    import configparser

    config = configparser.ConfigParser()
    config.read_file(args.config_file)

    problems = tuple(itertools.chain.from_iterable(
        f(ProxmoxAPI(**config[section]), **var_args)
        for section in args.section or config.sections()
    ))
    handle_result(merge_results(problems))
