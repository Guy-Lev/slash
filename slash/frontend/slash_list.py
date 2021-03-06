from __future__ import print_function

import argparse
import inspect
import itertools
import os
import sys
from functools import partial

import colorama
import slash
from slash.utils.cli_utils import UNDERLINED, make_styler
from slash.utils.python import get_underlying_func
from slash.utils.suite_files import iter_suite_file_paths

_heading_style = make_styler(colorama.Fore.MAGENTA + colorama.Style.BRIGHT + UNDERLINED)  # pylint: disable=no-member
_title_style = make_styler(colorama.Fore.WHITE + colorama.Style.BRIGHT)  # pylint: disable=no-member
_unused_style = make_styler(colorama.Fore.YELLOW)  # pylint: disable=no-member
_doc_style = make_styler(colorama.Fore.GREEN + colorama.Style.BRIGHT)  # pylint: disable=no-member


def _get_parser():
    parser = argparse.ArgumentParser('slash list [options] PATH...')
    parser.add_argument('-f', '--suite-file', dest='suite_files', action='append', default=[])
    parser.add_argument('--only-fixtures', dest='only', action='store_const', const='fixtures', default=None)
    parser.add_argument('--only-tests', dest='only', action='store_const', const='tests', default=None)
    parser.add_argument('--show-tags', dest='show_tags', action='store_true', default=False)
    parser.add_argument('--no-params', dest='show_params', action='store_false', default=True)
    parser.add_argument('--allow-empty', dest='allow_empty', action='store_true', default=False)
    parser.add_argument('paths', nargs='*', default=[], metavar='PATH')
    return parser


def slash_list(args, report_stream=sys.stdout):
    _print = partial(print, file=report_stream)
    _report_error = partial(print, file=sys.stderr)

    parser = _get_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.paths and not parsed_args.suite_files:
        parser.error('Neither test paths nor suite files were specified')

    with slash.Session() as session:
        slash.site.load()
        loader = slash.loader.Loader()
        runnables = loader.get_runnables(itertools.chain(parsed_args.paths, iter_suite_file_paths(parsed_args.suite_files)))
        used_fixtures = set()
        for test in runnables:
            used_fixtures.update(test.get_required_fixture_objects())

        if parsed_args.only in (None, 'fixtures'):
            _report_fixtures(parsed_args, session, _print, used_fixtures)

        if parsed_args.only in (None, 'tests'):
            _report_tests(parsed_args, runnables, _print)

    if len(runnables):
        return 0
    _report_error('No tests were found!')
    return not int(parsed_args.allow_empty)


def _report_tests(args, runnables, printer):
    if not args.only:
        printer(_heading_style('Tests'))

    visited = set()

    for runnable in runnables:
        extra = "" if not args.show_tags else "  Tags: {0}".format(list(runnable.get_tags()))
        address = runnable.__slash__.address
        if not args.show_params:
            address = address.split('(')[0]
        if address in visited:
            continue
        visited.add(address)
        printer("{0}{1}".format(_title_style(address), extra))


def _report_fixtures(args, session, printer, used_fixtures):
    if not args.only:
        printer(_heading_style('Fixtures'))
    for fixture in session.fixture_store:
        if not hasattr(fixture, 'fixture_func'):
            continue

        fixture_func = get_underlying_func(fixture.fixture_func)
        doc = inspect.cleandoc(fixture_func.__doc__) if fixture_func.__doc__ else ''

        unused_string = '' if fixture in used_fixtures else ' (Unused)'

        printer(_title_style('{0}{1}'.format(fixture.info.name, unused_string)))
        if doc:
            for line in (_doc_style(doc)).split('\n'):
                printer('    {0}'.format(line))

        printer('    Source: {0}:{1}'.format(
            os.path.relpath(inspect.getsourcefile(fixture_func), args.paths[0] if args.paths else '.'),
            inspect.getsourcelines(fixture_func)[1]))
        printer('\n')
