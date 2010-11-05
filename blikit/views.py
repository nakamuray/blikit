# vim: fileencoding=utf-8

import os

from werkzeug import redirect
from werkzeug.exceptions import NotFound

from blikit import urlmap
from blikit.models import BlobObject, LinkObject, TreeObject
from blikit.render import render_blob

# XXX: イメージです

READMES = [
    'README',
    'README.txt',
    'README.rst',
]

@urlmap.map_to('/<rev>/', defaults={'path': '/'})
@urlmap.map_to('/<rev>/<path:path>')
def view(ctx, rev, path):
    if path.endswith('/'):
        return tree(ctx, rev, path)
    else:
        return blob(ctx, rev, path)

def tree(ctx, rev, path):
    if rev == 'HEAD':
        commit_obj = ctx.odb.head
    else:
        commit_obj = ctx.odb.get_tree(rev)

    try:
        tree_obj = commit_obj.tree[path]

    except KeyError:
        raise NotFound('No such file or directory')

    if not isinstance(tree_obj, TreeObject):
        # TODO: follow symlink
        raise NotFound('No such file or directory')

    for readme_name in READMES:
        if readme_name in tree_obj:
            obj = tree_obj[readme_name]
            # TODO: follow symlink
            if isinstance(obj, BlobObject):
                readme = render_blob(obj)
                break

    else:
        readme = None

    return ctx.render_template('tree.html',
                               tree=tree_obj, readme=readme, context=ctx)

#@urlmap.map_to('/<rev>/<path:path>')
def blob(ctx, rev, path):
    if rev == 'HEAD':
        commit_obj = ctx.odb.head
    else:
        commit_obj = ctx.odb.get_tree(rev)

    blob_obj = commit_obj.tree[path]

    if isinstance(blob_obj, TreeObject):
        # redirect to same URL with trailing "/"
        return redirect(ctx.url_for('tree', rev=rev, path=path))
    elif isinstance(blob_obj, LinkObject):
        # TODO: follow symlink
        raise NotFound('No such file or directory')

    if 'raw' in ctx.request.args:
        content_type, encoding = mimetypes.guess_type(blob_obj.name)

        if content_type is None:
            if '\x00' in blob_obj.data:
                content_type = 'application/octat-stream'
            else:
                content_type = 'text/plain'

        # TODO: use encoding
        responce = Response(blob_obj.data,
                            content_type=content_type)
    else:
        doc = render_blob(ctx, blob_obj)
        responce = ctx.render_template('blob.html', doc=doc, context=ctx)

    return responce
