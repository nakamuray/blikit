from jinja2 import contextfilter
from werkzeug import escape, url_quote, url_quote_plus

from blikit.models import BlobObject, TreeObject
from blikit.render import render_blob

__all__ = ['escape_u', 'description']

def escape_u(url):
    return escape(url_quote_plus(url))

@contextfilter
def description(context, obj):
    ctx = context['context']

    if isinstance(obj, BlobObject):
        doc = render_blob(ctx, obj)
        return doc.title

    elif isinstance(obj, TreeObject):
        # TODO: search README and return README's title
        return None

    else:
        # TODO: LinkObject
        return None
