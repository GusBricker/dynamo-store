from dynamo_store.log import logger
from jsonpath_ng import jsonpath, parse

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def generate_paths(root_object, child_path=None):
    if child_path:
        child_path = remove_prefix(child_path, '$.')

    query = '*'
    for a in parse(query).find(root_object):
        is_item = False
        path = str(a.full_path)
        if child_path:
            if path.startswith(child_path):
                if '[' in path:
                    if path.count('.') == child_path.count('.') + 2:
                        is_item = True
                elif path.count('.') == child_path.count('.') + 1:
                    is_item = True
        elif '.' not in path and '[' not in path:
            is_item = True


        if isinstance(a.value, list):
            p = '%s[*]' % path
            root = root_object if isinstance(root_object, dict) else root_object.context
            b = parse(p).find(root)
            for c in b:
                if isinstance(c.value, dict):
                    logger.debug('%s: %s' % (str(c.full_path), is_item))
                    yield from generate_paths(c, child_path)
        elif isinstance(a.value, dict):
            yield from generate_paths(a, child_path)
        elif is_item:
            logger.debug('%s: %s [%s]' % (path, is_item, type(a.value)))
            yield a
