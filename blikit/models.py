import dulwich
import fnmatch
import os
import stat


class BaseObject(object):
    def __init__(self, odb, obj):
        self._odb = odb
        self._obj = obj
        self.sha = obj.sha()
        self.str_sha = self.sha.hexdigest()

        # will be setted by TreeObject or CommitObject
        self.parent = None
        self.name = None

    @property
    def abs_name(self):
        paths = [self.name]
        parent = self.parent

        while parent is not None:
            paths.insert(0, parent.name)
            parent = parent.parent

        return os.path.join(*paths)

    @property
    def last_modified(self):
        raise NotImplementedError


class BlobObject(BaseObject):
    @property
    def data(self):
        return self._obj.data


class LinkObject(BlobObject):
    @property
    def target(self):
        return self.data


class TreeObject(BaseObject):
    is_tree = True

    def iteritems(self):
        for name, _, _ in self._obj.iteritems():
            yield (name, self[name])

    def __iter__(self):
        return iter(self._obj)

    def __contains__(self, name):
        return name in self._obj

    def __getitem__(self, name):
        if '/' in name:
            return self._get_path(name)

        mode, hash = self._obj[name]

        if mode & stat.S_IFDIR:
            obj = self._odb.get_tree(hash)

        elif mode & stat.S_IFLNK:
            obj = self._odb.get_link(hash)

        else:
            obj = self._odb.get_blob(hash)

        obj.parent = self
        obj.name = name

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

    def find(self, name=None, type_=None, max_depth=None, reverse=False):
        if max_depth is not None:
            if max_depth == 0:
                return

            max_depth -= 1

        for obj_name, obj in sorted(self.iteritems(), reverse=reverse):
            if (type_ is None or isinstance(obj, type_)) and \
               (name is None or fnmatch.fnmatch(obj_name, name)):
                yield obj

            if isinstance(obj, TreeObject):
                for obj_ in obj.find(name, type_, max_depth, reverse):
                    yield obj_


class CommitObject(BaseObject):
    def __init__(self, repo, obj):
        super(CommitObject, self).__init__(repo, obj)
        self._tree = None
        self._parents = None

    @property
    def tree(self):
        if self._tree is None:
            self._tree = self._odb.get_tree(self._obj.tree)
            self._tree.name = '/'

        return self._tree

    @property
    def parents(self):
        if self._parents is None:
            self._parents = [self._odb.get_commit(hash)
                             for hash in self._obj.parents]

        # copy list
        return list(self._parents)

    def diff(self, other):
        if not isinstance(other, CommitObject):
            raise ObjectTypeMismatch('%s object expected, not %s' %
                                     (self.__class__.__name__, repr(other)))

        return self.tree.diff(other.tree)


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

    get_link = _make_get(dulwich.objects.Blob, BlobObject)

    get_tree = _make_get(dulwich.objects.Tree, TreeObject)

    get_commit = _make_get(dulwich.objects.Commit, CommitObject)

    @property
    def description(self):
        return self._repo.get_named_file('description').read()

    @property
    def head(self):
        return self.get_commit(self._repo.head())

    @property
    def histories(self):
        commit = self.head
        known_hashes = set(commit.str_sha)
        pending = [commit]
        while pending:
            commit = pending.pop(0)
            if commit.str_sha in known_hashes:
                continue

            known_hashes.add(commit.str_sha)

            yield commit

            pending.extend(commit.parents)
