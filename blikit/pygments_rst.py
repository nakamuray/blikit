from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.body import CodeBlock

# to provide backward compatibility, register `code` block as `sourcecode`
directives.register_directive('sourcecode', CodeBlock)
