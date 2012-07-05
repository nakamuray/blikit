# vim: fileencoding=utf-8

import mimetypes
import os

from cyclone.web import RequestHandler, HTTPError
from werkzeug.contrib.atom import AtomFeed

from blikit import utils
from blikit.models import BlobObject, LinkObject, TreeObject
from blikit.render import render_blob


class BaseHandler(RequestHandler):
    def initialize(self):
        self.odb = self.application.odb

    def render_string(self, template, **template_context):
        u'''render template using current jinja context

        return str
        '''
        context = {
            'handler': self,
            'reverse_url': self.reverse_url,
            'request': self.request,
        }

        context.update(template_context)

        html = self.application.jinja_env.get_template(template).render(**context)
        return html

    def render(self, template, **template_context):
        u'''render template using current jinja context and write directly
        '''
        html = self.render_string(template, **template_context)
        self.finish(html)

    def reverse_url(self, *args, **kwargs):
        # XXX: Tornado escape all args using cyclone.escape.url_escape, which
        #      escape "/" to "%2F".
        #      I don't intend that.
        url = super(BaseHandler, self).reverse_url(*args, **kwargs)
        return url.replace('%2F', '/')


class RootHandler(BaseHandler):
    def get(self):
        rev = 'HEAD' if self.odb.index is None else 'index'
        self.redirect(self.reverse_url('RootTreeHandler', rev))


class TreeHandler(BaseHandler):
    def get(self, rev, path='/'):
        if rev not in self.odb:
            raise HTTPError(404)

        if rev == 'HEAD':
            commit_obj = self.odb.head
        elif rev == 'index':
            commit_obj = self.odb.index
            if commit_obj is None:
                raise HTTPError(404, 'No such file or directory')
        else:
            commit_obj = self.odb.get_commit(rev)

        try:
            tree_obj = commit_obj.tree[path]

        except KeyError:
            raise HTTPError(404, 'No such file or directory')

        if not isinstance(tree_obj, TreeObject):
            raise HTTPError(404, 'No such file or directory')

        readme_obj = utils.find_readme(tree_obj)
        if readme_obj is not None:
            readme_doc = render_blob(self, readme_obj)
            readme = self.render_string('readme.html', doc=readme_doc)

        else:
            readme = None

        self.render('tree.html', commit=commit_obj, tree=tree_obj, readme=readme)


class BlobHandler(BaseHandler):
    def get(self, rev, path):
        if rev not in self.odb:
            raise HTTPError(404)

        if rev == 'HEAD':
            commit_obj = self.odb.head
        elif rev == 'index':
            commit_obj = self.odb.index
            if commit_obj is None:
                raise HTTPError(404, 'No such file or directory')
        else:
            commit_obj = self.odb.get_commit(rev)

        try:
            blob_obj = commit_obj.tree[path]

        except KeyError:
            raise HTTPError(404, 'No such file or directory')

        if isinstance(blob_obj, TreeObject):
            # redirect to same URL with trailing "/"
            return self.redirect(self.reverse_url('TreeHandler', rev, path+'/'))
        elif isinstance(blob_obj, LinkObject):
            raise HTTPError(404, 'No such file or directory')

        if self.get_argument('raw', default=False):
            content_type, encoding = mimetypes.guess_type(blob_obj.name)

            if content_type is None:
                if '\x00' in blob_obj.data:
                    content_type = 'application/octat-stream'
                else:
                    content_type = 'text/plain'

            # TODO: use encoding
            self.set_header('Content-Type', content_type)
            self.set_header('X-Robots-Tag', 'noindex')
            self.write(blob_obj.data)
        else:
            doc = render_blob(self, blob_obj)

            self.render('blob.html', doc=doc, blob=blob_obj, commit=commit_obj)


class AtomHandler(BaseHandler):
    def get(self):
        feed = AtomFeed(self.odb.name,
                        feed_url=self.reverse_url(type(self).__name__),
                        url=self.reverse_url('RootHandler'),
                        subtitle=self.odb.description)

        pattern = self.application.recent_doc_pattern

        for added_date, root_path in utils.recent_files(self, count=10,
                                                        pattern=pattern):
            blob_obj = self.odb.head.tree[root_path]
            assert isinstance(blob_obj, BlobObject)

            current_blob_obj = self.odb.head.tree[blob_obj.abs_name]

            doc = render_blob(self, current_blob_obj)
            url = 'http://' + self.request.host + \
                    self.reverse_url('BlobHandler', 'HEAD', blob_obj.root_path)
            feed.add(doc.title, doc.body, title_type='html', content_type='html',
                     author=doc.author_name, url=url,
                     updated=doc.last_modified, published=added_date)

        self.set_header('Content-Type', 'application/atom+xml')
        self.write(feed.to_string())
