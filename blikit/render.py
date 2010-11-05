# vim: fileencoding=utf-8

import fnmatch
import os
import werkzeug

from docutils import nodes
from docutils.core import publish_parts
from docutils.parsers.rst import Directive, directives

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import LEXERS, guess_lexer_for_filename, TextLexer

from blikit import utils
from blikit.models import BlobObject

class Document(object):
    title = None
    body = None
    def __init__(self, **attrs):
        for name, value in attrs.iteritems():
            if name.startswith('_'):
                continue
            setattr(self, name, value)


renderer_map = []

def register_for(*pats):
    def _register_for(func):
        for p in pats:
            renderer_map.append((p, func))
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

    for p, func in renderer_map:
        if fnmatch.fnmatch(blob_obj.name, p):
            result = func(ctx, blob_obj)
            break
    else:
        result = None

    return result


@register_for('*.txt')
def render_text(ctx, blob_obj):
    udata = blob_obj.data.decode('utf-8', 'replace')
    return Document(title=blob_obj.name,
                    body=u'<pre>' + werkzeug.escape(udata) + u'</pre>')


@register_for('*.rst')
def render_rst(ctx, blob_obj):
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


@register_for('*.png', '*.jpg', '*.jpeg', '*.gif')
def render_images(ctx, blob_obj):
    w, h = utils.calc_thumb_size(blob_obj.data, (640, 480))
    raw_url = werkzeug.escape(blob_obj.name) + '?raw=1'
    body = '<a href="%s"><img src="%s" width="%d" height="%s"></a>' % \
               (raw_url, raw_url, w, h)
    return Document(title=blob_obj.name, body=body)


formatter = HtmlFormatter(noclasses=True, linenos=True)

@register_for(*[p for l in LEXERS.values() for p in l[3]])
def render_sourcecode(ctx, blob_obj):
    try:
        data = blob_obj.data.decode('utf-8')

    except UnicodeDecodeError:
        data = blob_obj.data

    try:
        lexer = guess_lexer_for_filename(blob_obj.name, data)
    except ValueError:
        # no lexer found - use the text one instead of an exception
        lexer = TextLexer()

    return Document(title=blob_obj.name,
                    body=highlight(data, lexer, formatter))


@register_for('*')
def render_default(ctx, blob_obj):
    if '\x00' in blob_obj.data:
        # maybe binary file
        # display download link
        escaped = werkzeug.escape(blob_obj.name)
        body = '<a href="%s?raw=1">download "%s"</a>' % (escaped, escaped)
        return Document(title=blob_obj.name, body=body)

    else:
        # maybe some text file
        # render like *.txt
        return render_text(ctx, blob_obj)
