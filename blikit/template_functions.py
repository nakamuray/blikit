import collections

from jinja2 import contextfunction

from blikit import utils

__all__ = ['recent_files', 'pathentries']

@contextfunction
def recent_files(context, count=10):
    ctx = context['context']
    pattern = ctx.app.recent_doc_pattern
    Recent = collections.namedtuple('Recent', 'date blob')
    for commit_time, root_path in utils.recent_files(ctx, count,
                                                     pattern=pattern):
        yield Recent(commit_time.date(), ctx.odb.head.tree[root_path])

def pathentries(obj):
    result = []
    while obj.parent is not None:
        result.insert(0, obj)
        obj = obj.parent

    return result
