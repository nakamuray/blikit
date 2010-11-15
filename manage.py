#!/usr/bin/python
import os
import sys

from blikit.application import Blikit, is_git_repo
from werkzeug import script

if not is_git_repo('.'):
    print >> sys.stderr, 'not a git repository'
    sys.exit(0)

static = os.path.join(os.path.dirname(__file__), 'blikit', 'static')

action_runserver = script.make_runserver(lambda : Blikit('.'),
                                         use_reloader=True,
                                         use_debugger=True,
                                         static_files={'/static': static})
script.run()
