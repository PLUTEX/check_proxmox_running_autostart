import sys
import functools
from enum import IntEnum
from collections import namedtuple
from typing import Optional, Iterable, Callable


NagiosResult = namedtuple('NagiosResult', ['code', 'summary', 'details'])


class ResultCode(IntEnum):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3


def handle_result(result: NagiosResult) -> None:
    """Print and exit according to Nagios API specification

    :param result: The NagiosResult instance to use message and exit code from
    """
    if result.details:
        print('{}: {}\n{}'.format(
            result.code.name,
            result.summary,
            result.details,
        ))
    else:
        print('{}: {}'.format(
            result.code.name,
            result.summary,
        ))

    sys.exit(result[0])


def merge_results(
    results: Iterable[NagiosResult],
    summary: Optional[str] = None,
    fallback_code: ResultCode = ResultCode.OK,
) -> NagiosResult:
    """Merge multiple NagiosResult instances into one

    Take the worst result code of the results, join their details and set the
    given summary

    :param results: Iterable of results to merge
    :param summary: Summary to set on the resulting NagiosResult, defaults to
                    "There are N problems" where N is the number of items in
                    `results` without OK code
    :param fallback_code: Which code to set on the resulting NagiosResult when
                          there are no results (defaults to OK)
    :returns: The merged NagiosResult
    """
    results = tuple(results)
    if len(results) == 1:
        return results[0]

    return NagiosResult(
        code=max((result.code for result in results), default=fallback_code),
        summary=summary or 'There are {} problems'.format(
            sum(1 for result in results if result.code != ResultCode.OK)
        ),
        details='\n'.join(result.details for result in results),
    )


def unknown_on_exception(f: Callable):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except:  # noqa: E722
            exc_type, exc_value, exc_traceback = sys.exc_info()
            handle_result(NagiosResult(
                code=ResultCode.UNKNOWN,
                summary='{}: {}'.format(exc_type.__name__, str(exc_value)),
                details=str(exc_traceback),
            ))
