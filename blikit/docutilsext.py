import re

from docutils import nodes
from docutils.writers import html4css1

from blikit.models import TreeObject


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
    '''
    def visit_reference(self, node):
        print node
        if 'refuri' in node:
            refuri = node['refuri']
            if not re.match('^([a-z]+://|/)', refuri):
                # it's relative link
                # find file in vim like rule
                # - search relative to the directory of the current file
                # - search in the git root directory
                ctx = self.settings.ctx
                obj = self.settings.obj
                rev = 'HEAD' if ctx.odb.head == obj.commit else obj.commit.sha
                try:
                    ref_obj = obj.parent[refuri]
                    path = ref_obj.abs_name.strip('/')
                    if isinstance(ref_obj, TreeObject):
                        path = path + '/'
                    node['refuri'] = ctx.url_for('view_obj', rev=rev, path=path)

                except KeyError:
                    tree = obj.commit.tree
                    try:
                        ref_obj = tree[refuri]
                        path = ref_obj.abs_name.strip('/')
                        if isinstance(ref_obj, TreeObject):
                            path = path + '/'
                        node['refuri'] = ctx.url_for('view_obj', rev=rev, path=path)
                    except KeyError:
                        # can't find file, do nothing
                        pass

        return html4css1.HTMLTranslator.visit_reference(self, node)
