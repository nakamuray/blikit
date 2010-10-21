# vim: fileencoding=utf-8

import os

from werkzeug.exceptions import NotFound

from blik import urlmap, config
from blik.utils import to_html, render_template

# XXX: イメージです

@urlmap.map_to('/<rev>/', defaults={'path': '/'})
@urlmap.map_to('/<rev>/<path:path>/')
def tree(ctx, rev, path):
    if rev == 'HEAD':
        commit_obj = ctx.odb.head
    else:
        commit_obj = ctx.odb.get_tree(rev)

    # TODO: catch file not found error and return 404
    try:
        tree_obj = commit_obj.tree[path]

    except KeyError:
        raise NotFound('No such file or directory')

    if not isinstance(tree_obj, TreeObject):
        # TODO: follow symlink
        raise NotFound('No such file or directory')

    for readme_name in config.readmes:
        if readme_name in tree_obj:
            obj = tree_obj[readme_name]
            # TODO: follow symlink
            if isinstance(obj, BlobObject):
                _, ext = os.path.splitext(readme_name)
                readme = render_blob(obj)
                break

    else:
        readme = None

    return render_template('tree.html',
                           tree=tree_obj, readme=readme, context=ctx)

@urlmap.map_to('/<rev>/<path:path>')
def blob(ctx, rev, path):
    if rev == 'HEAD':
        commit_obj = ctx.odb.head
    else:
        commit_obj = ctx.odb.get_tree(rev)

    blob_obj = commit_obj.tree.get_path(path)
    # TODO: follow symlink

    _, ext = os.path.splitext(path)
    doc = render_blob(blob_obj)

    return render_template('blob.html', doc=doc, context=ctx)
