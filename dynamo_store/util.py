from dynamo_store.log import logger
from jsonpath_ng import jsonpath, parse

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def generate_paths(root_object):
    query = '*'
    for a in parse(query).find(root_object):
        path = str(a.full_path)
        logger.debug(path)

        if isinstance(a.value, list):
            p = '%s[*]' % path
            root = root_object if isinstance(root_object, dict) else root_object.context
            b = parse(p).find(root)

            logger.debug('%s: [%s]' % (path, type(a.value)))
            yield a

            for c in b:
                if isinstance(c.value, dict):
                    logger.debug('%s: [%s]' % (str(c.full_path), type(c.value)))
                    yield from generate_paths(c)
        elif isinstance(a.value, dict):
            yield from generate_paths(a)
        else:
            logger.debug('%s: [%s]' % (path, type(a.value)))
            yield a
