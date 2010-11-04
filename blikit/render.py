# vim: fileencoding=utf-8

import werkzeug

from docutils import nodes
from docutils.core import publish_parts
from docutils.parsers.rst import Directive, directives

class Document(object):
    title = None
    body = None
    def __init__(self, **attrs):
        for name, value in attrs:
            if name.startswith('_'):
                continue
            setattr(self, name, value)


renderer_map = dict()

def register_for(*exts):
    def _register_for(func):
        for e in exts:
            renderer_map[e] = func
        return func

    return _register_for


def render_blob(ctx, blob_obj):
    u'''render BlobObject as HTML portion using proper render function

    return <Document object>

    if there is no render function for this object, return None
    '''
    if not isinstance(blob_obj, BlobObject):
        # TODO: raise proper exception
        # XXX: may this function treat TreeObject?
        raise Exception

    _, ext = os.path.splitext(blob_obj.name)
    if ext in renderer_map:
        result = renderer_map[ext](blob_obj)
    else:
        result = None

    return result


@register_for('.txt')
def render_text(blob_obj):
    return Document(title=blob_obj.name,
                    boty='<pre>' + werkzeug.escape(blob_obj.data) + '</pre>')


@register_for('.rst')
def render_rst(blob_obj):
    parts = publish_parts(blob_obj.data, writer_name='html',
                          settings_overrides={'tree': tree})
    return Document(**parts)


class IncludeTree(Directive):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'recursive': directives.flag,
        'name': directives.unchanged,
        'reverse': directives.flag,
        'limit': directives.positive_int,
    }

    def run(self):
        tree = self.state.document.settings.tree
        path = self.arguments[0]
        limit = self.options.get('limit', None)
        for i, blob in enumerate(tree.find()):
            if limit is not None and i > limit:
                break

            # TODO: convert to HTML
            yield nodes.raw('', str(blob), format='html')

directives.register_directive('include-tree', IncludeTree)
