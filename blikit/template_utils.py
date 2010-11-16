from werkzeug import escape, url_quote, url_quote_plus

from blikit.models import BlobObject, TreeObject

__all__ = ['escape_u']

def escape_u(url):
    return escape(url_quote_plus(url))
