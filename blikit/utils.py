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
