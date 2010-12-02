blikit is web based git repository browser, document viewer or something like it.

requirements
============

- python
- git
- Jinja2
- PIL
- Pygments
- Werkzeug
- docutils
- dulwich


install
=======

::

  $ python setup.py install


run
===

blikit ship with ``blikit-manage.py`` script to run built-in web server.

::

  $ cd /path/to/git/repository
  $ blikit-manage.py runserver
   * Running on http://localhost:5000/
   * Restarting with reloader...

or use ``blikit.application.Blikit(repo_path)`` with your favorite WSGI servers.


reStructuredText extensions
===========================

blikit uses reStructuredText with some extensions.

- relative link's target is searched with vim's ``gf`` like rules

  + search relative to the directory of the current file
  + search in the git root directory

- ``show-contents`` directive that show all(or `count` number of) files under the `directory`::

    .. show-contents:: directory
       :no-recursive:
       :reverse:
       :count: 10
       :pattern: *.rst
       :show-hidden:

- ``sourcecode`` directive to highlight sourcecode using pygments::

    .. sourcecode:: python

       for i in range(10):
           print 'hello world'
