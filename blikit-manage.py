#!/usr/bin/python
import os
import sys

import blikit

from blikit.application import Blikit, is_git_repo
from werkzeug import script
from werkzeug.contrib import profiler

if not is_git_repo('.'):
    print >> sys.stderr, 'not a git repository'
    sys.exit(0)

def make_app():
    return Blikit('.')

static = os.path.join(os.path.dirname(blikit.__file__), 'static')

action_runserver = script.make_runserver(make_app,
                                         static_files={'/static': static})

action_develop = script.make_runserver(make_app,
                                       use_reloader=True,
                                       use_debugger=True,
                                       static_files={'/static': static})

action_profile = profiler.make_action(make_app,
                                      stream=open('/tmp/profiler.log', 'w'))

script.run()
