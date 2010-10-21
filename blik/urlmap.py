from werkzeug.routing import Map, Rule

_url_map = Map()

def map_to(rule, **kwargs):
    def decorate(f):
        kwargs['endpoint'] = f.__name__
        _url_map.add(Rule(rule, **kwargs))
        return f

    return decorate

def bind_to_envidon(*args, **kwargs):
    return _url_map.bind_to_environ(*args, **kwargs)

def url_for(url_adapter, endpoint, _external=False, **values):
    return url_adapter.build(endpoint, values, force_external=_external)
