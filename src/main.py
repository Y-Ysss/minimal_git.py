import argparse
import pathlib
import sys

import data_objects
import file_system
import index

__version__ = '0.0.1'


def command_version():
    print('Version:', __version__)


def command_help(args):
    print('@', sys._getframe().f_code.co_name)
    print(argparse.ArgumentParser().parse_args([args.command, '--help']))


def command_init(args):
    print('@', sys._getframe().f_code.co_name)
    file_system.make_base_dirs()
    index.update_ref('HEAD', f'refs/heads/{data_objects.MAIN_BRANCH}')


def command_add(args):
    print('@', sys._getframe().f_code.co_name)
    index.add(args.patterns)


def command_commit(args):
    print('@', sys._getframe().f_code.co_name)


def command_debug(args):
    print('@', sys._getframe().f_code.co_name)
    print('@', args)
    if args.ignore_list:
        print(file_system.ignore_list())


def argment_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    # parser.set_defaults(handler=command_help)

    commands = parser.add_subparsers(dest='command')

    parsetr_version = commands.add_parser('version')
    parsetr_version.set_defaults(handler=command_version)

    parser_help = commands.add_parser('init')
    parser_help.set_defaults(handler=command_init)

    parser_help = commands.add_parser('help')
    parser_help.set_defaults(handler=command_help)

    parser_debug = commands.add_parser('debug')
    parser_debug.add_argument('-igl', '--ignore-list', action='store_true')
    parser_debug.set_defaults(handler=command_debug)

    parser_add = commands.add_parser('add')
    parser_add.add_argument('-A', '--all', action='store_true', help='all files')
    parser_add.set_defaults(handler=command_add)
    parser_add.add_argument('patterns', nargs='+', type=pathlib.Path, default="-")

    parser_add = commands.add_parser('as')
    parser_add.set_defaults(handler=test)
    parser_add.add_argument('patterns', nargs='+')

    parser_commit = commands.add_parser('commit')
    parser_commit.add_argument('-m', metavar='msg', help='commit message')
    parser_commit.set_defaults(handler=command_commit)

    return parser

def test(args):
    print('@', sys._getframe().f_code.co_name)
    for pattern in args.patterns:
        for path in pathlib.Path().glob(pattern):
            print(path)


def main():
    parser = argment_parser()
    args = parser.parse_args()

    print('@', args)
    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
