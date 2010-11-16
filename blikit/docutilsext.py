import re

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.writers import html4css1

from blikit.models import TreeObject
import blikit.render


class Writer(html4css1.Writer):
    '''docutils.writers.html4css1.Writer class with extended HTMLTranslator
    '''
    def __init__(self):
        html4css1.Writer.__init__(self)
        self.translator_class = HTMLTranslator


class HTMLTranslator(html4css1.HTMLTranslator):
    '''docutils.writers.html4css1.HTMLTranslator with some extentions

    - search link target with vim's ``gf`` like rule

      + search relative to the directory of the current file
      + search in the git root directory

    - append "?raw=1" to image's URL
    '''
    def visit_reference(self, node):
        refuri = self.gf_if_relative_link(node['refuri'])
        if refuri is not None:
            node['refuri'] = refuri
        return html4css1.HTMLTranslator.visit_reference(self, node)

    def visit_image(self, node):
        uri = self.gf_if_relative_link(node['uri'])
        if uri is not None:
            node['uri'] = uri + '?raw=1'
        return html4css1.HTMLTranslator.visit_image(self, node)

    def gf_if_relative_link(self, uri):
        if not re.match('^([a-z]+://|/)', uri):
            # it's relative link
            ctx = self.settings.ctx
            obj = self.settings.obj

            ref_obj = self.gf(ctx, obj, uri)
            if ref_obj is not None:
                rev = obj.commit.name
                path = ref_obj.abs_name.strip('/')

                if isinstance(ref_obj, TreeObject):
                    path = path + '/'

                return ctx.url_for('view_obj', rev=rev, path=path)

        return None

    @staticmethod
    def gf(ctx, obj, path):
        '''
        find file in vim like rule

        - search relative to the directory of the current file
        - search in the git root directory

        return Blob/Tree/LinkObject or None if no file found
        '''
        try:
            return obj.parent[path]

        except KeyError:
            tree = obj.commit.tree
            try:
                return tree[path]

            except KeyError:
                # can't find file
                return None


class ShowContents(Directive):
    has_content = False
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        'recursive': directives.flag,
        'order_by': lambda x: directives.choice(x, ('name', 'last_modified')),
        'reverse': directives.flag,
        'count': directives.positive_int,
        'pattern': directives.unchanged,
        'show-hidden': directives.flag,
    }

    def run(self):
        ctx = self.state.document.settings.ctx

        obj = self.state.document.settings.obj
        if isinstance(obj, TreeObject):
            tree = obj
        else:
            tree = obj.parent

        if self.arguments:
            path = self.arguments[0]

            try:
                if path.startswith('/'):
                    tree = obj.commit.tree[path]

                else:
                    tree = tree[path]
            except KeyError, e:
                error = self.state_machine.reporter.error(
                    'directory not found "%s"' % path,
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno
                )
                return [error]

        order_by = self.options.get('order_by', 'name')
        if order_by == 'name':
            key_func = lambda x: x.name

        elif order_by == 'last_modified':
            key_func = lambda x: x.last_modified

        rev = self.options.get('reverse', False)

        max_count = self.options.get('count', None)
        count = 0
        result = []

        is_recursive = self.options.get('recursive', True)

        show_hidden = self.options.get('show-hidden', False)

        for root, dirs, files in tree.walk():
            files.sort(key=key_func, reverse=rev)
            for f in files:
                if f.name.startswith('.') and not show_hidden:
                    # skip hidden file
                    continue

                # TODO: filter by pattern
                count += 1
                doc = blikit.render.render_blob(ctx, f)
                html = ctx.render_template('innerdoc.html', doc=doc, context=ctx)
                result.append(nodes.raw('', html, format='html'))

                if max_count is not None and count >= max_count:
                    break

            if not is_recursive:
                break

            if not show_hidden:
                # remove hidden dirs
                dirs[:] = filter(lambda d: not d.name.startswith('.'), dirs)

            dirs.sort(key=key_func, reverse=rev)

        return result

directives.register_directive('show-contents', ShowContents)

import pygments_rst
