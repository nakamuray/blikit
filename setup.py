from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES

import glob

# Tell distutils to put the data_files in platform-specific installation
# locations. See here for an explanation:
# http://groups.google.com/group/comp.lang.python/browse_thread/thread/35ec7b2fed36eaec/2105ee4d9e8042cb
for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

setup(
    name = 'blikit',
    version = '0.2',
    packages = ['blikit'],
    install_requires = [
        'Jinja2',
        'Pillow',
        'Pygments',
        'Werkzeug',
        'docutils >= 0.9',
        'dulwich',
    ],
    scripts = ['blikit-manage.py'],
    data_files = [('blikit/static', glob.glob('blikit/static/*')),
                  ('blikit/templates', glob.glob('blikit/templates/*'))],
)

