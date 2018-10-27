from dynamo_store.store import DyStore
from dynamo_store.log import logger
import importlib
from jsonmodels import models, fields, errors, validators
import builtins
import importlib

builtin_types = tuple(getattr(builtins, t) for t in dir(builtins) if isinstance(getattr(builtins, t), type))

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
    config_loader(DyObject.CONFIG_LOADER_DICT_TO_KEY, key=key, value=value)
    :param config: DyObject.CONFIG_LOADER_DICT_TO_CLASS
    :param key: key in parent object
    :param value: value of dict in object
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

    @classmethod
    def _value_from_meta(cls, meta):
        klass = meta['__class__']
        module = meta['__module__']
        module = importlib.import_module(module)
        class_ = getattr(module, klass)

        new = class_(meta['value'])
        return new

    @staticmethod
    def _is_value_meta_dict(meta):
        if not isinstance(meta, dict):
            return False
        return meta.get('__class__') and meta.get('__module__') and meta.get('__metatype__') == 'value'

    @staticmethod
    def _is_shard_meta_dict(meta):
        if not isinstance(meta, dict):
            return False
        return meta.get('__class__') and meta.get('__module__') and meta.get('__metatype__') == 'shard'

    @staticmethod
    def _value_to_classinfo(value):
        d = {}
        if isinstance(value, type):
            if value in builtin_types:
                d['__class__'] = value.__qualname__
                d['__module__'] = 'builtins'
            else:
                d['__class__'] = value.__qualname__
                d['__module__'] = value.__module__
        else:
            if isinstance(value, builtin_types):
                d['__class__'] = value.__class__.__qualname__
                d['__module__'] = 'builtins'
            else:
                d['__class__'] = value.__class__.__qualname__
                d['__module__'] = value.__module__
        return d

    @staticmethod
    def _check_value_meta_type(meta, type_):
        if not DyObject._is_value_meta_dict(meta):
            return False

        classinfo = DyObject._value_to_classinfo(type_)
        return meta.get('__class__') == classinfo.get('__class__') and \
               meta.get('__module__') == classinfo.get('__module__')

    @staticmethod
    def _meta_value(meta):
        return meta['value']

    def _value_to_meta(self, value):
        d = DyObject._value_to_classinfo(value)
        d['value'] =  value
        d['__metatype__'] = 'value'
        return d

    def to_dict(self, path="", shards=None):
        d = {'__class__': self.__class__.__qualname__,
             '__module__': self.__module__,
             '__metatype__': 'shard'}
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
                value_list = [None] * len(value)
                for index in range(len(value)):
                    v = value[index]
                    if isinstance(v, DyObject):
                        if v.TABLE_NAME and v.PRIMARY_KEY_NAME and v.REGION_NAME:
                            p = "%s.%s.value[%d]" % (path, name, index)
                            shard = DyStore(table_name=v.TABLE_NAME,
                                            primary_key_name=v.PRIMARY_KEY_NAME,
                                            path=p,
                                            region=v.REGION_NAME)
                            shards.append(shard)
                            logger.debug('Found shard: %s' % p)

                        value_list[index] = v.to_dict(path="$", shards=shards)
                    else:
                        value_list[index] = self._value_to_meta(v)
                d[name] = self._value_to_meta(value_list)
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
                    d[name] = self._value_to_meta(value)

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
            class_ = config_loader(DyObject.CONFIG_LOADER_DICT_TO_CLASS, key=key, value=value)

            if class_ and issubclass(class_, DyObject):
                logger.debug('Instantiating: %s' % class_)
                child_obj = class_.from_dict(value, config_loader=config_loader)
                return child_obj
        elif cls.CONFIG_LOADER and callable(cls.CONFIG_LOADER):
            class_ = cls.CONFIG_LOADER(DyObject.CONFIG_LOADER_DICT_TO_CLASS, key=key, value=value)
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

            if DyObject._check_value_meta_type(value, list):
                value = DyObject._meta_value(value)
                items = [None] * len(value)
                for index in range(len(value)):
                    v = value[index]
                    if DyObject._is_shard_meta_dict(v):
                        items[index] = cls._load_dict(key, v, config_loader)
                    elif DyObject._is_value_meta_dict(v):
                        items[index] = DyObject._value_from_meta(v)
                    else:
                        items[index] = v
                setattr(obj, key, items)
            elif isinstance(value, dict) and not DyObject._is_value_meta_dict(value):
                setattr(obj, key, cls._load_dict(key, value, config_loader))
            elif DyObject._is_value_meta_dict(value):
                setattr(obj, key, cls._value_from_meta(value))
            else:
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
        self.to_dict(path="$", shards=shards)
        logger.debug(shards)

        if not primary_key:
            primary_key = getattr(self, '__primary_key', None)
            if primary_key:
                logger.debug('Found existing pk %s' % primary_key)

        cls = self.__class__
        if not config_loader or not callable(config_loader):
            if cls.CONFIG_LOADER and callable(cls.CONFIG_LOADER):
                config_loader = cls.CONFIG_LOADER

        if self.store(shards=shards).delete(primary_key, config_loader=config_loader):
            logger.debug('Storing pk %s' % primary_key)
            setattr(self, '__primary_key', primary_key)
            return True

        return False

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
