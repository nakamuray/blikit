import collections

from jinja2 import contextfunction

from blikit import utils

__all__ = ['recent_files']

@contextfunction
def recent_files(context, count=10):
    odb = context['context'].odb
    Recent = collections.namedtuple('Recent', 'date blob')
    for commit_time, blob_obj in utils.recent_files(odb, count):
        yield Recent(commit_time.date(), blob_obj)
