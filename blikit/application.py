# vim: fileencoding=utf-8
import os
import time

from jinja2 import Environment, FileSystemLoader
from jinja2.ext import loopcontrols, with_

from werkzeug import Request, ClosingIterator, SharedDataMiddleware, \
        peek_path_info, pop_path_info
from werkzeug.contrib.cache import NullCache, FileSystemCache
from werkzeug.exceptions import HTTPException, NotFound

from blikit import models, views, template_filters, template_functions
from blikit.context import Context

DEFAULT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates')

class Blikit(object):
    '''Blikit WSGI application
    '''
    def __init__(self, repo_path,
                 site_name=None, site_description=None, static_links=None,
                 recent_doc_pattern=None):
        '''
        repo_pash: path to git repository
        site_name: name of this site,
                   use repository directory name if not passed
        site_description: description of this site,
                          use contents of "description" file in git repository
                          if not passed
        static_links: [('name of link', 'URL')],
                      static links displayed at sidebar
        recent_doc_pattern: only files match this pattern are displayed in
                            sidebar and atom
        '''
        self._repo_path = repo_path
        self._odb = models.ObjectDatabase(repo_path)
        self._init_jinja_env()
        self._init_cache()

        if site_name is None:
            site_name = self._odb.name

        self.site_name = site_name

        if site_description is None:
            site_description = self._odb.description

        self.site_description = site_description

        if static_links is None:
            static_links = []

        self.static_links = static_links

        self.recent_doc_pattern = recent_doc_pattern

        static = os.path.join(os.path.dirname(__file__), 'static')
        self._static_app = SharedDataMiddleware(NotFound(), {'/static': static})

    def _init_jinja_env(self):
        template_path_list = [DEFAULT_TEMPLATE_PATH]

        repo_template_path = os.path.join(self._repo_path, 'templates')
        if os.path.isdir(repo_template_path):
            template_path_list.append(repo_template_path)

        jinja_env = Environment(loader=FileSystemLoader(template_path_list),
                                extensions=[loopcontrols, with_])

        # add template filters
        for name in template_filters.__all__:
            jinja_env.filters[name] = getattr(template_filters, name)

        # add template functions
        for name in template_functions.__all__:
            jinja_env.globals[name] = getattr(template_functions, name)

        self._jinja_env = jinja_env

    def _init_cache(self):
        default_timeout = 86400

        cache_dir = os.path.join(self._odb.controldir, 'blikit-cache')
        if os.path.isdir(cache_dir):
            if os.access(cache_dir, os.R_OK|os.W_OK|os.X_OK):
                self.cache = FileSystemCache(cache_dir,
                                             default_timeout=default_timeout)
            else:
                self.cache = NullCache()

        elif os.access(self._repo_path, os.W_OK):
            os.mkdir(cache_dir)
            self.cache = FileSystemCache(cache_dir,
                                         default_timeout=default_timeout)

        else:
            self.cache = NullCache()


    def __call__(self, environ, start_response):
        if peek_path_info(environ) == 'static':
            return self._static_app(environ, start_response)

        context = Context(self, environ, self._odb, self._jinja_env)
        try:
            endpoint, values = context.url_adapter.match()
            handler = getattr(views, endpoint)
            response = handler(context, **values)
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response), [])


def is_git_repo(path):
    u'''return whether path is git repository or not

    simply check git repository specific files/directories are exists
    '''
    if os.path.isdir(os.path.join(path, '.git')):
        # git repository with work directory
        return True

    for f in ['HEAD', 'config', 'description']:
        if not os.path.isfile(os.path.join(path, f)):
            return False

    for d in ['branches', 'hooks', 'info', 'objects', 'refs']:
        if not os.path.isdir(os.path.join(path, d)):
            return False

    # git bare repository
    return True


class BlikitDir(object):
    refresh_interval = 60

    def __init__(self, path):
        self._path = path

        self._last_checked = 0
        self._apps = {}

        self.find_repositories()

    def __call__(self, environ, start_response):
        app_name = peek_path_info(environ)
        if app_name in self._apps:
            pop_path_info(environ)
            return self._apps[app_name](environ, start_response)
        else:
            #resp = Response('404 Not Found',
            #                status=404, content_type='text/plain')
            resp = NotFound()
            return resp(environ, start_response)

    def find_repositories(self):
        dirs = os.path.listdir(self._path)

        # add new repositories
        for dir_name in dirs:
            dir_path = os.path.join(self._path, dir_name)

            if is_git_repo(dir_path) and dir_name not in self._apps:
                self._apps[dir_name] = Blikit(dir_path)

        # remove repositories that does not exists anymore
        for dir_name in self._apps:
            if not is_git_repo(os.path.join(self._path, dir_name)):
                del self._apps[dir_name]

        self._last_checked = time.time()
