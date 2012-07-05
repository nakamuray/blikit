#!/usr/bin/python
import argparse
import os
import sys

from twisted.internet import reactor
from twisted.python import log

from blikit.application import Blikit, is_git_repo

parser = argparse.ArgumentParser(description='Blikit management command')

parser.add_argument('--hostname', default='localhost')
parser.add_argument('--port', default=5000, type=int)
# TODO: run application with werkzeug's debugger and profiler if specified
#define('debug', default=False, type=bool, help='enable debugger')
#define('profile', default=False, type=bool, help='enable profiler')

options = parser.parse_args()

if not is_git_repo('.'):
    print >> sys.stderr, 'not a git repository'
    sys.exit(0)

application = Blikit('.')
log.startLogging(sys.stdout)
reactor.listenTCP(options.port, application, interface=options.hostname)
print 'http://{0}:{1}/'.format(options.hostname, options.port)
reactor.run()
