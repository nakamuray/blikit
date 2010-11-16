# vim: fileencoding=utf-8

import mimetypes
import os

from werkzeug import Response, redirect
from werkzeug.exceptions import NotFound

from blikit import urlmap, utils
from blikit.models import BlobObject, LinkObject, TreeObject
from blikit.render import render_blob

@urlmap.map_to('/')
def root(ctx):
    return redirect(ctx.url_for('view_obj', rev='HEAD'))

@urlmap.map_to('/<rev>/', defaults={'path': '/'})
@urlmap.map_to('/<rev>/<path:path>')
def view_obj(ctx, rev, path):
    # XXX: Rule('/<rev>/<path:path>/') が末尾の "/" が無くてもマッチする上に
    #      勝手に "/" 付きの URL にリダイレクトを試みてくれるので、
    #      blob view の方に行き着けない。
    #      かといって Rule('/<rev>/<path:path>') を前に持ってくると "/" で終わる
    #      URL にも普通にマッチしてしまうので、今度は tree view の方に行けない。
    #
    #      ということで仕方なくここで判定・ルーティングする。
    if path.endswith('/'):
        return tree(ctx, rev, path)
    else:
        return blob(ctx, rev, path)

#@urlmap.map_to('/<rev>/', defaults={'path': '/'})
#@urlmap.map_to('/<rev>/<path:path>')
def tree(ctx, rev, path):
    if rev == 'HEAD':
        commit_obj = ctx.odb.head
    else:
        commit_obj = ctx.odb.get_commit(rev)

    try:
        tree_obj = commit_obj.tree[path]

    except KeyError:
        raise NotFound('No such file or directory')

    if not isinstance(tree_obj, TreeObject):
        # TODO: follow symlink
        raise NotFound('No such file or directory')

    readme_obj = utils.find_readme(tree_obj)
    if readme_obj is not None:
        readme_doc = render_blob(ctx, readme_obj)
        readme = ctx.render_template('doc.html', doc=readme_doc)

    else:
        readme = None

    pathentries = []
    t = tree_obj
    while t.parent is not None:
        pathentries.insert(0, t)
        t = t.parent

    return ctx.render_to_response('tree.html',
                                  commit=commit_obj, tree=tree_obj,
                                  pathentries=pathentries, readme=readme)

#@urlmap.map_to('/<rev>/<path:path>')
def blob(ctx, rev, path):
    if rev == 'HEAD':
        commit_obj = ctx.odb.head
    else:
        commit_obj = ctx.odb.get_commit(rev)

    try:
        blob_obj = commit_obj.tree[path]

    except KeyError:
        raise NotFound('No such file or directory')

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

        pathentries = []
        t = blob_obj.parent
        while t.parent is not None:
            pathentries.insert(0, t)
            t = t.parent

        responce = ctx.render_to_response('blob.html',
                                          doc=doc, blob=blob_obj,
                                          commit=commit_obj, pathentries=pathentries)

    return responce
