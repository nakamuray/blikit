import Image

from cStringIO import StringIO

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
