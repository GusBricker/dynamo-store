from dynamo_store.store import DyStore
from dynamo_store.log import logger
import importlib

class DyObject(object):
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
    If this object is a child of another DyObject, then this is
    the json path to this child from its parent
    """
    PATH = None

    """
    Invoked on object load when class cant be determined.
    config_loader(DyObject.CONFIG_LOADER_DICT_TO_KEY, {'key': key, 'value': value})
    :param key: DyObject.CONFIG_LOADER_DICT_TO_CLASS
    :param data: key in parent object, value of dict in object
    :returns: Class to instantiate, None if to keep as dict
    """
    CONFIG_LOADER_DICT_TO_CLASS = 'dict'

    def __init__(self):
        self.__primary_key = None

    @property
    def store(self):
        return DyStore(table_name=self.TABLE_NAME,
                       primary_key_name=self.PRIMARY_KEY_NAME,
                       path=self.PATH,
                       region=self.REGION_NAME)

    def to_dict(self):
        d = {'__class__': self.__class__.__qualname__,
             '__module__': self.__module__}
        for name in dir(self):
            value = getattr(self, name)
            if name.startswith('__') or callable(value) or name == 'store':
                continue

            if isinstance(value, DyObject):
                d[name] = value.to_dict()
            else:
                d[name] = value
        return d

    @staticmethod
    def from_dict(obj, data, config_loader=None):
        for key, value in data.items():
            if isinstance(value, dict):
                if value.get('__class__') and value.get('__module__'):
                    klass = value['__class__']
                    module = value['__module__']
                    module = importlib.import_module(module)
                    class_ = getattr(module, klass)
                    logger.debug('Instantiating: %s' % class_)
                    child_obj = class_()
                    class_.from_dict(child_obj, value, config_loader=config_loader)
                    setattr(obj, key, child_obj)
                elif config_loader and callable(config_loader):
                    class_ = config_loader(DyObject.CONFIG_LOADER_DICT_TO_CLASS, {'key': key, 'value': value})
                    if class_ and issubclass(class_, DyObject):
                        logger.debug('Instantiating: %s' % class_)
                        child_obj = class_()
                        class_.from_dict(child_obj, value, config_loader=config_loader)
                        setattr(obj, key, child_obj)
                    else:
                        setattr(obj, key, value)
                else:
                    setattr(obj, key, value)
            elif key not in ['__class__', '__module__']:
                setattr(obj, key, value)

    def save(self, primary_key=None, config_loader=None):
        """
        Saves this object to the store.
        :param primary_key: Primary key to use.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: key of object written
        """
        d = self.to_dict()
        if not primary_key:
            if hasattr(self, "__primary_key") and self.__primary_key:
                primary_key = self.__primary_key

        key = self.store.write(d, primary_key=primary_key, config_loader=config_loader)
        if key:
            self.__primary_key = key

        return key

    @classmethod
    def load(cls, primary_key, config_loader=None):
        """
        Loads an object from the store.
        :param cls: Class to instantiate
        :param primary_key: Primary key of object to load.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: cls object
        """
        obj = cls()
        success, data = obj.store.read(primary_key, config_loader=config_loader)
        if not success:
            raise Exception('Couldnt read from store using pk: %s' % primary_key)
        cls.from_dict(obj, data, config_loader=config_loader)
        return obj