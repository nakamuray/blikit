# vim: fileencoding=utf-8

import mimetypes
import os

from werkzeug import Response, redirect
from werkzeug.contrib.atom import AtomFeed
from werkzeug.exceptions import NotFound

from blikit import urlmap, utils
from blikit.models import BlobObject, LinkObject, TreeObject
from blikit.render import render_blob

@urlmap.map_to('/')
def root(ctx):
    if ctx.odb.index is not None:
        return redirect(ctx.url_for('view_obj', rev='index'))
    else:
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
    elif rev == 'index':
        commit_obj = ctx.odb.index
        if commit_obj is None:
            raise NotFound('No such file or directory')
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
    elif rev == 'index':
        commit_obj = ctx.odb.index
        if commit_obj is None:
            raise NotFound('No such file or directory')
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

@urlmap.map_to('/atom')
def atom(ctx):
    feed = AtomFeed(ctx.odb.name,
                    feed_url=ctx.url_for('atom'),
                    url=ctx.url_for('root'),
                    subtitle=ctx.odb.description)

    for added_date, blob_obj in utils.recent_files(ctx.odb, count=10):
        assert isinstance(blob_obj, BlobObject)

        current_blob_obj = ctx.odb.head.tree[blob_obj.abs_name]

        doc = render_blob(ctx, current_blob_obj)
        url = 'http://' + ctx.request.host + \
                ctx.url_for('view_obj', rev='HEAD', path=blob_obj.root_path)
        feed.add(doc.title, doc.body, content_type='html',
                 author=blob_obj.commit.author_name, url=url,
                 updated=blob_obj.last_modified, published=added_date)

    return feed.get_response()
