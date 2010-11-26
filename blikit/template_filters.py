from jinja2 import contextfilter
from werkzeug import escape, url_quote, url_quote_plus

from blikit import utils
from blikit.models import BlobObject, TreeObject, LinkObject
from blikit.render import render_blob

__all__ = ['escape_u', 'document', 'description', 'title', 'dateformat',
           'is_tree']

def escape_u(url):
    return escape(url_quote_plus(url))

@contextfilter
def document(context, obj):
    ctx = context['context']
    return render_blob(ctx, obj)

@contextfilter
def description(context, obj):
    ctx = context['context']

    if isinstance(obj, BlobObject):
        doc = render_blob(ctx, obj)
        return doc.description

    elif isinstance(obj, TreeObject):
        readme_obj = utils.find_readme(obj)
        if readme_obj is not None:
            readme_doc = render_blob(ctx, readme_obj)
            return readme_doc.description

    else:
        # TODO: LinkObject
        pass

@contextfilter
def title(context, obj):
    ctx = context['context']

    if isinstance(obj, BlobObject):
        doc = render_blob(ctx, obj)
        return doc.title

    elif isinstance(obj, TreeObject):
        readme_obj = utils.find_readme(obj)
        if readme_obj is not None:
            readme_doc = render_blob(ctx, readme_obj)
            return readme_doc.title

    else:
        # TODO: LinkObject
        pass

def dateformat(datetime, fmt='%Y-%m-%d %H:%M'):
    return datetime.strftime(fmt)

def is_tree(obj):
    return isinstance(obj, TreeObject)
