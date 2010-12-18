import bisect
import fnmatch
import Image

from cStringIO import StringIO

from blikit.models import BlobObject, TreeObject, ObjectTypeMismatch

def get_image_size(data):
    img = Image.open(StringIO(data))
    return img.size

def calc_thumb_size(data, max_size):
    w, h = get_image_size(data)
    max_w, max_h = max_size

    ratio_w = max_w * 1.0 / w
    ratio_h = max_h * 1.0 / h

    if ratio_w > 1 and ratio_h > 1:
        return (w, h)
    elif ratio_w > ratio_h:
        return (w * ratio_h, max_h)
    else:
        return (max_w, h * ratio_w)

READMES = [
    'README',
    'README.txt',
    'README.rst',
    '.README',
    '.README.txt',
    '.README.rst',
]

def find_readme(tree_obj):
    if not isinstance(tree_obj, TreeObject):
        raise ObjectTypeMismatch

    for readme_name in READMES:
        if readme_name in tree_obj:
            obj = tree_obj[readme_name]
            # TODO: follow symlink
            if isinstance(obj, BlobObject):
                return obj

    return None

def recent_files(ctx, count=None, path=None, pattern=None, show_hidden=False):
    '''search recently added files

    return [(datetime.datetime when file created, root_path)]
    '''
    cache_key = 'utils.recent_files:%s:%s:%s:%s' % \
            (ctx.odb.head.sha, repr(path), repr(pattern), show_hidden)
    cached = ctx.app.cache.get(cache_key)
    if cached is not None:
        cached_count, cached_result = cached
        if cached_count == count:
            return cached_result

        elif cached_count > count:
            return cached_result[:count]

    odb = ctx.odb
    args = ['--date-order']

    if path is None:
        path = '/'
    else:
        git_args.extend(['--', path])

    added_names = set()
    results = []

    for commit_hash in odb.git('log', *args, format='format:%H'):
        commit_obj = odb.get_commit(commit_hash)
        added_in_this_commit = []

        # TODO: if path is not TreeObject
        tree_obj = commit_obj.tree[path]

        if not commit_obj.parents:
            # initial commit
            # all files is added in this commit
            added_in_this_commit = tree_obj.find(type_=BlobObject)

        elif len(commit_obj.parents) == 1:
            parent_commit = commit_obj.parents[0]
            parent_tree = parent_commit.tree[path]
            try:
                a, _, _ = tree_obj.diff(parent_tree)

                for obj in a:
                    if isinstance(obj, TreeObject):
                        added_in_this_commit.extend(obj.find(type_=BlobObject))
                    elif isinstance(obj, BlobObject):
                        added_in_this_commit.append(obj)

            except KeyError:
                # parent commit's tree does not have this path
                # so all files under this path added in this commit
                added_in_this_commit = tree_obj.find(type_=BlobObject)

        elif len(commit_obj.parents) >= 2:
            s = None
            for parent_commit in commit_obj.parents:
                parent_tree = parent_commit.tree[path]
                a, _, _ = tree_obj.diff(parent_tree)

                if s is None:
                    s = set(a)
                else:
                    # files not shown in all parent's tree
                    # is added in this merge commit
                    s.intersection_update(a)

            for obj in s:
                if isinstance(obj, TreeObject):
                    added_in_this_commit.extend(obj.find(type_=BlobObject))
                elif isinstance(obj, BlobObject):
                    added_in_this_commit.append(obj)

        for obj in added_in_this_commit:
            # to hide dot directories find "/." in obj.abs_name
            if isinstance(obj, BlobObject) and \
               (show_hidden or '/.' not in obj.abs_name) and \
               obj.abs_name not in added_names and \
               fnmatch.fnmatch(obj.name, pattern) and \
               obj.abs_name in odb.head.tree:
                added_names.add(obj.abs_name)
                bisect.insort_right(results,
                                    (commit_obj.commit_time, obj.root_path))

        if count is not None:
            while len(results) > count:
                # remove oldest value
                results.pop(0)

    results.reverse()

    if cached is None or cached_count < count:
        ctx.app.cache.set(cache_key, (count, results))

    return results
