# vim: fileencoding=utf-8

from docutils import nodes
from docutils.core import publish_parts
from docutils.parsers.rst import Directive, directives


def render(ctx, blob_obj, file_name):
    pass


def render_rst(ctx, blob_obj):
    parts = publish_parts(blob_obj.data, writer_name='html',
                          settings_overrides={'tree': tree})


class IncludeTree(Directive):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'recursive': directives.flag,
        'name': directives.unchanged,
        'reverse': directives.flag,
        'limit': directives.positive_int,
    }

    def run(self):
        tree = self.state.document.settings.tree
        path = self.arguments[0]
        limit = self.options.get('limit', None)
        for i, blob in enumerate(tree.find()):
            if limit is not None and i > limit:
                break

            # TODO: convert to HTML
            yield nodes.raw('', str(blob), format='html')

directives.register_directive('include-tree', IncludeTree)
