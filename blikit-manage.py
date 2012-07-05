#!/usr/bin/python
import os
import sys

from tornado import ioloop
from tornado.options import define, options, parse_command_line

from blikit.application import Blikit, is_git_repo

define('hostname', default='localhost')
define('port', default=5000, type=int)
# TODO: run application with werkzeug's debugger and profiler if specified
#define('debug', default=False, type=bool, help='enable debugger')
#define('profile', default=False, type=bool, help='enable profiler')

parse_command_line()

if not is_git_repo('.'):
    print >> sys.stderr, 'not a git repository'
    sys.exit(0)

application = Blikit('.')
application.listen(options.port, options.hostname)
print 'http://{0}:{1}/'.format(options.hostname, options.port)
ioloop.IOLoop.instance().start()
