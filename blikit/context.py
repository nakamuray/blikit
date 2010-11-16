# vim: fileencoding=utf-8
from werkzeug import Request, Response

from blikit import urlmap

class Context(object):
    u'''Store contexts for current HTTP access

    Context object hold these attributes:

    request
      werkzeug.Request object for current HTTP access

    odb
      blikit.models.ObjectDatabase object

    url_adapter
      werkzeug.routing.MapAdapter object
      that is bound to current HTTP environment

    jinja_env
      jinja2.Environment object
    '''
    __slots__ = ['request', 'odb', 'url_adapter', 'jinja_env']

    def __init__(self, environ, odb, jinja_env):
        self.request = Request(environ)
        self.odb = odb
        self.url_adapter = urlmap.bind_to_environ(environ)
        self.jinja_env = jinja_env

    def url_for(self, endpoint, _external=False, **values):
        u'''generate URL for endpoint for current environ
        '''
        return urlmap.url_for(self.url_adapter, endpoint, _external, **values)

    def render_template(self, template, **template_context):
        u'''render template using current jinja context

        return str
        '''
        context = {
            'context': self,
            'url_for': self.url_for,
            'request': self.request,
        }

        context.update(template_context)

        html = self.jinja_env.get_template(template).render(**context)
        return html

    def render_to_response(self, template, **template_context):
        u'''render template using current jinja context

        return werkzeug.Response object
        '''
        html = self.render_template(template, **template_context)
        return Response(html, mimetype='text/html')
