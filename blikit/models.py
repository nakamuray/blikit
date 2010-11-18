import collections
import datetime
import dulwich
import fnmatch
import os
import stat

from subprocess import Popen, PIPE


class BaseObject(object):
    def __init__(self, odb, obj):
        self._odb = odb
        self._obj = obj
        self.sha = obj.sha().hexdigest()

        # will be setted by TreeObject or CommitObject
        self.parent = None
        self.name = None

        # will be setted through set_commit
        self._commit_sha = None

    @property
    def abs_name(self):
        paths = [self.name]
        parent = self.parent

        while parent is not None:
            paths.insert(0, parent.name)
            parent = parent.parent

        return os.path.join(*paths)

    @property
    def root_path(self):
        return self.abs_name.lstrip('/')

    @property
    def last_modified(self):
        visited = set()
        pendings = [self.commit]
        abs_name = self.abs_name
        while pendings:
            commit = pendings.pop(0)
            visited.add(commit.sha)

            for parent_commit in commit.parents:
                if parent_commit in visited:
                    continue

                try:
                    obj_sha = parent_commit.tree[abs_name].sha
                except KeyError:
                    obj_sha = None

                if self.sha == obj_sha:
                    # if this commit's file has same sha,
                    # the file was altered somewhere in this branch (correct?)
                    pendings.append(parent_commit)
                    break
            else:
                # all parents has different sha,
                # so this file was altered by this commit
                return commit.commit_time

        # maybe initial commit
        return commit.commit_time

    @property
    def commit(self):
        if self._commit_sha is None:
            # index
            return self._odb.index

        else:
            return self._odb.get_commit(self._commit_sha)

    def set_commit(self, commit_obj):
        if isinstance(commit_obj, CommitObject):
            # record hash to avoid circular reference
            self._commit_sha = commit_obj.sha

        elif isinstance(commit_obj, basestring):
            self._commit_sha = commit_obj

        elif commit_obj is None:
            # maybe IndexObject's sha
            self._commit_sha = None

        else:
            raise ObjectTypeMismatch

    def __eq__(self, other):
        if hasattr(other, 'sha'):
            return self.sha == other.sha
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.sha)


class BlobObject(BaseObject):
    _size = None

    @property
    def data(self):
        return self._obj.data

    @property
    def size(self):
        if self._size is None:
            self._size = len(self.data)
        return self._size


class LinkObject(BaseObject):
    @property
    def target(self):
        return self.data


class TreeObject(BaseObject):
    is_tree = True

    def iteritems(self):
        for name, _, _ in self._obj.iteritems():
            yield (name, self[name])

    def itervalues(self):
        for _, f in self.iteritems():
            yield f

    def __iter__(self):
        return iter(self._obj)

    def __contains__(self, name):
        if '/' in name:
            try:
                self[name]
                return True
            except KeyError:
                return False
        else:
            return name in self._obj

    def __getitem__(self, name):
        if '/' in name:
            return self._get_path(name)

        if name == '.':
            return self

        elif name == '..':
            if self.parent:
                return self.parent
            else:
                # / (root)
                return self

        mode, hash = self._obj[name]

        if mode & stat.S_IFDIR:
            obj = self._odb.get_tree(hash)

        elif (mode & stat.S_IFLNK) == stat.S_IFLNK:
            obj = self._odb.get_link(hash)

        else:
            obj = self._odb.get_blob(hash)

        obj.parent = self
        obj.name = name
        obj.set_commit(self._commit_sha)

        return obj

    def _get_path(self, path):
        path = path.strip('/')

        if path == '':
            return self

        if '/' in path:
            dirname, subpath = path.split('/', 1)
            subdir = self[dirname]

            if not isinstance(subdir, TreeObject):
                #raise ObjectTypeMismatch('Not a directory')
                raise KeyError

            return subdir[subpath]

        else:
            return self[path]

    def walk(self, topdown=True):
        roots = collections.deque([self])

        while roots:
            root = roots.popleft()
            dirs = []
            files = []

            for f in root.itervalues():
                if isinstance(f, BlobObject):
                    files.append(f)
                elif isinstance(f, TreeObject):
                    dirs.append(f)
                else:
                    # TODO: what to do with LinkObject(?)
                    pass

            yield root, dirs, files

            if topdown:
                roots.extendleft(dirs)
            else:
                roots.extend(dirs)

    def diff(self, other):
        '''show differences of two trees

        return ([added object], [removed object], [modified object])
        '''
        added = []
        removed = []
        modified = []

        my_contents = dict(self.iteritems())
        for k, v in other.iteritems():
            if k in my_contents:
                my_v = my_contents[k]
                if my_v != v:
                    if isinstance(my_v, TreeObject):
                        a, r, m = my_v.diff(v)
                        added.extend(a)
                        removed.extend(r)
                        modified.extend(m)

                    else:
                        modified.append(my_v)

                del my_contents[k]

        added.extend(my_contents.values())

        return (added, removed, modified)

    def find(self, name=None, type_=BaseObject, max_depth=None, reverse=False):
        if max_depth is not None:
            if max_depth == 0:
                return

            max_depth -= 1

        for obj_name, obj in sorted(self.iteritems(), reverse=reverse):
            if (isinstance(obj, type_)) and \
               (name is None or fnmatch.fnmatch(obj_name, name)):
                yield obj

            if isinstance(obj, TreeObject):
                for obj_ in obj.find(name, type_, max_depth):
                    yield obj_


class CommitObject(BaseObject):
    def __init__(self, repo, obj):
        super(CommitObject, self).__init__(repo, obj)
        self._tree = None
        self._parents = None

        if self.sha == self._odb._repo.head():
            self.name = 'HEAD'
        else:
            self.name = self.sha

    @property
    def tree(self):
        if self._tree is None:
            self._tree = self._odb.get_tree(self._obj.tree)
            self._tree.name = '/'
            self._tree.set_commit(self)

        return self._tree

    @property
    def parents(self):
        if self._parents is None:
            self._parents = [self._odb.get_commit(hash)
                             for hash in self._obj.parents]

        # copy list
        return list(self._parents)

    @property
    def commit_time(self):
        return datetime.datetime.fromtimestamp(self._obj.commit_time, _TO(self._obj.commit_timezone))

    def diff(self, other=None):
        '''show differences of two commits

        return ([added object], [removed object], [modified object])
        '''
        if other is None:
            # FIXME: when has no parents
            # FIXME: when has many parents
            other = self.parents[0]

        if not isinstance(other, CommitObject):
            raise ObjectTypeMismatch('%s object expected, not %s' %
                                     (self.__class__.__name__, repr(other)))

        return self.tree.diff(other.tree)

class _TO(datetime.tzinfo):
    zero = datetime.timedelta(0)
    def __init__(self, sec_offset):
        self._offset = datetime.timedelta(seconds=sec_offset)
    def utcoffset(self, dt):
        return self._offset
    def tzname(self, dt):
        return None
    def dst(self, dt):
        return self.zero


class IndexObject(CommitObject):
    def __init__(self, odb, index):
        self._index = index

        self._odb = odb
        self._obj = None
        self.sha = None

        self.parent = None
        self.name = 'index'

        self._tree = None
        self._parents = None

    @property
    def tree(self):
        if self._tree is None:
            tree_sha = self._index.commit(self._odb.object_store)
            self._tree = self._odb.get_tree(tree_sha)
            self._tree.name = '/'
            self._tree.set_commit(self)

        return self._tree

    @property
    def parents(self):
        return [self._odb.head]

    @property
    def commit_time(self):
        return datetime.datetime.now()


class ObjectTypeMismatch(Exception):
    pass


class ObjectDatabase(object):
    def __init__(self, repo):
        if not isinstance(repo, dulwich.repo.BaseRepo):
            repo = dulwich.repo.Repo(repo)

        self._repo = repo

    def _make_get(expected_class, return_class):
        def _get_object(self, hash):
            obj = self._repo.get_object(hash)

            if not isinstance(obj, expected_class):
                raise ObjectTypeMismatch('%s object expected, not %s' %
                                         (expected_class.__name__, repr(obj)))

            return return_class(self, obj)
        return _get_object

    get_blob = _make_get(dulwich.objects.Blob, BlobObject)

    get_link = _make_get(dulwich.objects.Blob, LinkObject)

    get_tree = _make_get(dulwich.objects.Tree, TreeObject)

    get_commit = _make_get(dulwich.objects.Commit, CommitObject)

    @property
    def description(self):
        return self._repo.get_named_file('description').read()

    @property
    def head(self):
        return self.get_commit(self._repo.head())

    @property
    def index(self):
        if self._repo.has_index():
            return IndexObject(self, self._repo.open_index())
        else:
            return None

    @property
    def object_store(self):
        return self._repo.object_store

    @property
    def histories(self):
        commit = self.head
        known_hashes = set(commit.sha)
        pending = [commit]
        while pending:
            commit = pending.pop(0)
            if commit.sha in known_hashes:
                continue

            known_hashes.add(commit.sha)

            yield commit

            pending.extend(commit.parents)

    def git(self, *args, **kwargs):
        '''call git command

        return generator object of output lines
        '''
        cmdargs = ['git']
        cmdargs.extend(args)
        cmdargs.extend('--%s=%s' % kv for kv in kwargs.iteritems())
        try:
            p = Popen(cmdargs, stdout=PIPE, cwd=self._repo.path)
            for line in p.stdout:
                yield line.rstrip('\r\n')
        except GeneratorExit:
            p.stdout.close()
            p.wait()
