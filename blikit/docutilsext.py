import fnmatch
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
        if 'refuri' in node:
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
            handler = self.settings.handler
            obj = self.settings.obj

            ref_obj = self.gf(handler, obj, uri)
            if ref_obj is not None:
                rev = obj.commit.name
                path = ref_obj.abs_name.strip('/')

                if isinstance(ref_obj, TreeObject):
                    path = path + '/'
                    return handler.application.reverse_url('TreeHandler', rev, path)

                else:
                    return handler.application.reverse_url('BlobHandler', rev, path)

        return None

    @staticmethod
    def gf(handler, obj, path):
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
        'no-recursive': directives.flag,
        'order_by': lambda x: directives.choice(x, ('name', 'last_modified')),
        'reverse': directives.flag,
        'count': directives.positive_int,
        'pattern': directives.unchanged,
        'show-hidden': directives.flag,
    }

    def run(self):
        is_recursive = not 'no-recursive' in self.options
        order_by = self.options.get('order_by', 'name')
        is_reverse = 'reverse' in self.options
        max_count = self.options.get('count', None)
        pattern = self.options.get('pattern', None)
        show_hidden = 'show-hidden' in self.options

        handler = self.state.document.settings.handler

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

        if order_by == 'name':
            key_func = lambda x: x.name

        elif order_by == 'last_modified':
            key_func = lambda x: x.last_modified

        count = 0
        result = []

        for root, dirs, files in tree.walk():
            files.sort(key=key_func, reverse=is_reverse)
            for f in files:
                if f.name.startswith('.') and not show_hidden:
                    # skip hidden file
                    continue

                if pattern is not None and not fnmatch.fnmatch(f.name, pattern):
                    continue

                count += 1
                doc = blikit.render.render_blob(handler, f)
                html = handler.render_string('innerdoc.html', doc=doc, blob=f,
                                             commit=f.commit, handler=handler)
                result.append(nodes.raw('', html, format='html'))

                if max_count is not None and count >= max_count:
                    # break inner loop
                    break

            if max_count is not None and count >= max_count:
                # break outer loop
                break

            if not is_recursive:
                break

            if not show_hidden:
                # remove hidden dirs
                dirs[:] = filter(lambda d: not d.name.startswith('.'), dirs)

            dirs.sort(key=key_func, reverse=is_reverse)

        return result

directives.register_directive('show-contents', ShowContents)

import pygments_rst
