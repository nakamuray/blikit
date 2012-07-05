from jinja2 import contextfilter

from blikit import utils
from blikit.models import BlobObject, TreeObject, LinkObject
from blikit.render import render_blob

__all__ = ['document', 'description', 'title', 'dateformat',
           'is_tree', 'is_link']

@contextfilter
def document(context, obj):
    handler = context['handler']
    return render_blob(handler, obj)

@contextfilter
def description(context, obj):
    handler = context['handler']

    if isinstance(obj, BlobObject):
        doc = render_blob(handler, obj)
        return doc.description

    elif isinstance(obj, TreeObject):
        readme_obj = utils.find_readme(obj)
        if readme_obj is not None:
            readme_doc = render_blob(handler, readme_obj)
            return readme_doc.description

    else:
        # TODO: LinkObject
        pass

@contextfilter
def title(context, obj):
    handler = context['handler']

    if isinstance(obj, BlobObject):
        doc = render_blob(handler, obj)
        return doc.title

    elif isinstance(obj, TreeObject):
        readme_obj = utils.find_readme(obj)
        if readme_obj is not None:
            readme_doc = render_blob(handler, readme_obj)
            return readme_doc.title

    else:
        # TODO: LinkObject
        pass

def dateformat(datetime, fmt='%Y-%m-%d %H:%M'):
    return datetime.strftime(fmt)

def is_tree(obj):
    return isinstance(obj, TreeObject)

def is_link(obj):
    return isinstance(obj, LinkObject)
