from dynamo_store.store import DyStore
from dynamo_store.log import logger
import importlib
from jsonmodels import models, fields, errors, validators

class DyObject(models.Base):
    """
    Name of table in AWS to save this object to.
    """
    TABLE_NAME = None

    """
    Region in AWS to save this object to.
    """
    REGION_NAME = None

    """
    Name of primary key to use for this object.
    """
    PRIMARY_KEY_NAME = None

    """
    Config loader callable to use when config queries are made
    """
    CONFIG_LOADER = None

    """
    Variable names to ignore during serialization
    """
    IGNORE_LIST = []

    """
    Invoked on object load when class cant be determined.
    config_loader(DyObject.CONFIG_LOADER_DICT_TO_KEY, {'key': key, 'value': value})
    :param key: DyObject.CONFIG_LOADER_DICT_TO_CLASS
    :param data: key in parent object, value of dict in object
    :returns: Class to instantiate, None if to keep as dict
    """
    CONFIG_LOADER_DICT_TO_CLASS = 'dict'

    @classmethod
    def store(cls, shards, path=None):
        return DyStore(table_name=cls.TABLE_NAME,
                       primary_key_name=cls.PRIMARY_KEY_NAME,
                       path=path,
                       shards=shards,
                       region=cls.REGION_NAME)

    def to_dict(self, path="", shards=None):
        d = {'__class__': self.__class__.__qualname__,
             '__module__': self.__module__}
        ignore_keys = ['CONFIG_LOADER', 'CONFIG_LOADER_DICT_TO_CLASS', 'IGNORE_LIST', 'REGION_NAME', 'TABLE_NAME', 'PRIMARY_KEY_NAME'] \
                        + self.IGNORE_LIST
        logger.debug(self.to_struct())
        for name in dir(self):
            if name in ignore_keys:
                continue

            value = getattr(self, name)
            if name.startswith('_') or callable(value):
                continue

            if isinstance(value, list):
                d[name] = [None] * len(value)
                for index in range(len(value)):
                    v = value[index]
                    if isinstance(v, DyObject):
                        if v.TABLE_NAME and v.PRIMARY_KEY_NAME and v.REGION_NAME:
                            p = "%s.%s[%d]" % (path, name, index)
                            shard = DyStore(table_name=v.TABLE_NAME,
                                            primary_key_name=v.PRIMARY_KEY_NAME,
                                            path=p,
                                            region=v.REGION_NAME)
                            shards.append(shard)
                            logger.debug('Found shard: %s' % p)

                        d[name][index] = v.to_dict(path="$", shards=shards)
                    else:
                        d[name][index] = v
            else:
                if isinstance(value, DyObject):
                    if value.TABLE_NAME and value.PRIMARY_KEY_NAME and value.REGION_NAME:
                        p = "%s.%s" % (path, name)
                        shard = DyStore(table_name=value.TABLE_NAME,
                                        primary_key_name=value.PRIMARY_KEY_NAME,
                                        path=p,
                                        region=value.REGION_NAME)
                        shards.append(shard)
                        logger.debug('Found shard: %s' % p)
                    d[name] = value.to_dict(path="$", shards=shards)
                else:
                    d[name] = value
        return d

    @classmethod
    def _load_dict(cls, key, value, config_loader):
        if value.get('__class__') and value.get('__module__'):
            klass = value['__class__']
            module = value['__module__']
            module = importlib.import_module(module)
            class_ = getattr(module, klass)
            logger.debug('Instantiating: %s' % class_)
            child_obj = class_.from_dict(value, config_loader=config_loader)
            return child_obj
        elif config_loader and callable(config_loader):
            class_ = config_loader(DyObject.CONFIG_LOADER_DICT_TO_CLASS, {'key': key, 'value': value})

            if class_ and issubclass(class_, DyObject):
                logger.debug('Instantiating: %s' % class_)
                child_obj = class_.from_dict(value, config_loader=config_loader)
                return child_obj
        elif cls.CONFIG_LOADER and callable(cls.CONFIG_LOADER):
            class_ = cls.CONFIG_LOADER(DyObject.CONFIG_LOADER_DICT_TO_CLASS, {'key': key, 'value': value})
            if class_ and issubclass(class_, DyObject):
                logger.debug('Instantiating: %s' % class_)
                child_obj = class_.from_dict(value, config_loader=config_loader)
                return child_obj

        return value

    @classmethod
    def from_dict(cls, data, config_loader=None):
        obj = cls()
        ignore_keys = ['__class__', '__module__'] + cls.IGNORE_LIST

        for key, value in data.items():
            if key in ignore_keys:
                continue

            if isinstance(value, list):
                items = [None] * len(value)
                for index in range(len(value)):
                    v = value[index]
                    items[index] = cls._load_dict(key, v, config_loader)
                setattr(obj, key, items)

            elif isinstance(value, dict):
                setattr(obj, key, cls._load_dict(key, value, config_loader))
            elif key not in ['__class__', '__module__']:
                setattr(obj, key, value)
        return obj

    def delete(self, primary_key=None, config_loader=None):
        """
        Delete an object from the store.
        :param primary_key: Primary key to use, (optional: value passed in will be stored in instance for future use).
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: True if successful, False otherwise
        """
        shards = []
        d = self.to_dict(path="$", shards=shards)
        logger.debug(shards)

        if not primary_key:
            primary_key = getattr(self, '__primary_key', None)
            if primary_key:
                logger.debug('Found existing pk %s' % primary_key)

        cls = self.__class__
        if not config_loader or not callable(config_loader):
            if cls.CONFIG_LOADER and callable(cls.CONFIG_LOADER):
                config_loader = cls.CONFIG_LOADER

        if self.store(shards=shards).delete(d, primary_key, config_loader=config_loader):
            logger.debug('Storing pk %s' % primary_key)
            setattr(self, '__primary_key', primary_key)

        return True

    def save(self, primary_key=None, config_loader=None):
        """
        Saves this object to the store.
        :param primary_key: Primary key to use, (optional: value passed in will be stored in instance for future use).
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: key of object written on success, None otherwise
        """
        shards = []
        d = self.to_dict(path="$", shards=shards)
        logger.debug(shards)

        if not primary_key:
            primary_key = getattr(self, '__primary_key', None)
            if primary_key:
                logger.debug('Found existing pk %s' % primary_key)

        cls = self.__class__
        if not config_loader or not callable(config_loader):
            if cls.CONFIG_LOADER and callable(cls.CONFIG_LOADER):
                config_loader = cls.CONFIG_LOADER

        key = self.store(shards=shards).write(d, primary_key=primary_key, config_loader=config_loader)
        if key:
            logger.debug('Storing pk %s' % key)
            setattr(self, '__primary_key', key)

        return key

    @classmethod
    def load(cls, primary_key, config_loader=None, validate=True):
        """
        Loads an object from the store.
        :param cls: Class to instantiate
        :param primary_key: Primary key of object to load.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :param validate: Enable JSON Models field validation
        :returns: cls object
        """
        if not config_loader or not callable(config_loader):
            if cls.CONFIG_LOADER and callable(cls.CONFIG_LOADER):
                config_loader = cls.CONFIG_LOADER

        success, data = cls.store(shards=[]).read(primary_key, config_loader=config_loader)
        if not success:
            raise Exception('Couldnt read from store using pk: %s' % primary_key)
        logger.debug(data)
        obj = cls.from_dict(data, config_loader=config_loader)
        setattr(obj, '__primary_key', primary_key)
        if validate:
            obj.validate()
        return obj
