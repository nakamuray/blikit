from werkzeug import escape, url_quote, url_quote_plus

def escape_u(url):
    return escape(url_quote_plus(url))
