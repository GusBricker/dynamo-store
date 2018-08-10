# dynamo-store

[![Downloads](https://img.shields.io/badge/objectpath--ng-downloads-brightgreen.svg)](https://pypi.python.org/pypi/dynamo-store/)
[![License](https://img.shields.io/badge/license-GPLv2-blue.svg)](https://pypi.python.org/pypi/dynamo-store/)
[![Build Status](https://travis-ci.org/objectpath/ObjectPath.svg?branch=master)](https://travis-ci.org/objectpath/dynamo-store)

dynamo-store is a Python library designed to make multi-sharded data structure storage in DynamoDB seamless.

Out of the box it supports:
- Automatic sharding of child dictionaries into other tables (useful for getting around 400KB limit of DyanmoDB)
- Encryption of data at rest using 128bit AES_CBC
- Automagic serialization of objects to tables

## Example DyStore usage

```
from dynamo_store.store import DyStore

def root_store():
    shards = [DyStore('Shard1', 'IDX', path='$.birth_details'),
              DyStore('Shard2', 'IDX', path='$.location')]
    return DyStore('Root', 'ID', shards=shards)

def loader(config, data):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        encrypted_paths = ['birth_details.hospital', 'birth_details.dob', 'location.city', 'location.country', 'firstname', 'lastname']
        if data in encrypted_paths:
            return 'somekey'
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

d = {'firstname': 'john',
     'lastname': 'smith',
     'location': {'city': 'Osaka',
                  'country': 'Japan'},
     'birth_details': {'hospital': 'Kosei Nenkin',
                       'dob': '12/2/1995'}}

# Write object to store
key = root_store().write(d)

# Update individual path
root_store().write_path(key, "location.city", "New York")

# Read back object from store
success, obj = root_store().read(key)

# Read individual path
path = root_store().read_path(key, "location.country")

# Delete object from store
root_store().delete(key)
```

## Example DyObject usage

```
class BirthDetails(DyObject):
    TABLE_NAME = 'Shard1'       # Table to save this shard to in AWS
    REGION_NAME = 'us-east-2'   # Region to sav eto in AWS
    PRIMARY_KEY_NAME = 'IDX'    # Primary key name to use
    PATH = '$.birth_details'    # Path in Root object

    def __init__(self):
        self.hospital = None
        self.dob = None

class Location(DyObject):
    TABLE_NAME = 'Shard2'       # Table to save this shard to in AWS
    REGION_NAME = 'us-east-2'   # Region to save to in AWS
    PRIMARY_KEY_NAME = 'IDX'    # Primary key name to use
    PATH = '$.location'         # Path in Root object

    def __init__(self):
        self.city = None
        self.country = None

class Root(DyObject):
    TABLE_NAME = 'Root'         # Table to save to in AWS
    REGION_NAME = 'us-east-2'   # Region to save to in AWS
    PRIMARY_KEY_NAME = 'ID'     # Primary key name to use

    def __init__(self):
        self.firstname = None
        self.lastname = None
        self.location = Location()
        self.birth_details = BirthDetails()

def loader(config, data):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        encrypted_paths = ['birth_details.hospital', 'birth_details.dob', 'location.city', 'location.country', 'firstname', 'lastname']
        if data in encrypted_paths:
            return 'somekey'
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False
    elif config == DyObject.CONFIG_LOADER_DICT_TO_CLASS:
        # In this case we can just use the dict key to determine what kind of object it is
        # other cases might require examining the value
        key = data['key']
        if key == 'location':
            return Location
        elif key == 'birth_details':
            return BirthDetails
        elif key == 'geolocation':
            return GeoLocation

    return None

# Setup and save object 
orig = Root()
orig.firstname = 'john'
orig.lastname = 'smith'
orig.location.city = 'Osaka'
orig.location.country = 'Kewpie'
orig.birth_details.dob = '15/03/1980'
orig.birth_details.hospital = 'Good one'
key = orig.save(config_loader=loader)

# Load object using key obtained from save() call
o = Root.load(key, config_loader=loader)
print(o.firstname)
print(o.lastname)
print(o.location.city)
print(o.location.country)
print(o.birth_details.dob)
print(o.birth_details.hospital)
```


### DyStore API
```
class DyStore(object):
    """
    Invoked on writes to allow control of primary key.
    config_loader(DyStore.CONFIG_LOADER_GENERATE_PK, item)
    :param key: DyStore.CONFIG_LOADER_GENERATE_PK
    :param data: item being written
    :returns: string containing primary key to use, None to use uuid4()
    """
    CONFIG_LOADER_GENERATE_PK = 'pk'

    """
    Invoked on decryption/encryption to control key used.
    config_loader(DyStore.CONFIG_LOADER_LOAD_KEY, path)
    :param key: DyStore.CONFIG_LOADER_LOAD_KEY
    :param data: json path of item being encrypted/decrypted
    :returns: string containing key to use, None to ignore decryption/encryption
    """
    CONFIG_LOADER_LOAD_KEY = 'key'

    """
    Invoked on read/write to control if DyStore metadata should be kept in object.
    config_loader(DyStore.CONFIG_LOADER_KEEP_METADATA, item)
    :param key: DyStore.CONFIG_LOADER_KEEP_METADATA
    :param data: item being read/written
    :returns: bool controlling if metadata should be kept or not
    """
    CONFIG_LOADER_KEEP_METADATA = 'meta'

    def __init__(self, table_name=None, primary_key_name=None, path=None, shards=[], region='us-east-2'):
        """
        :param table_name: Name of DynamoDB table this object will access
        :param primary_key_name: Primary key name in DynamoDB
        :param path: JSON Path of this object when it is used in a shard, note: see jsonpath-ng for documentation on jsonpath.
        :param shards: Items to shard out to other tables in this object.
        :param region: AWS region for table.
        """

    def read_path(self, primary_key, path, config_loader=None):
        """
        Reads a path from an object from this store.
        :param primary_key: Primary key of object to read.
        :param path: JSON path of object to read (can reside in a shard).
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: list of values on success, None otherwise
        """

    def read(self, primary_key, resolve_shards=True, config_loader=None):
        """
        Reads an object from this store.
        :param primary_key: Primary key of object to read.
        :param resolve_shards: Boolean to control whether shards are read.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: success, value
        """

    def write_path(self, primary_key, path, value, config_loader=None):
        """
        Writes a path in an object to this store.
        :param primary_key: Primary key of object to read.
        :param path: JSON path of object to read (can reside in a shard).
        :param value: Value to write at the JSON path.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :param root_object: Internal parameter used for proper path resolution in config load calls.
        :returns: True if successful, False otherwise
        """

    def write(self, data, primary_key=None, save_shards=True, config_loader=None):
        """
        Writes an object to this store.
        :param primary_key: Primary key of object to write.
        :param save_shards: Boolean to control whether shards are saved.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: primary_key used/generated
        """

    def delete(self, primary_key, delete_shards=True, config_loader=None):
        """
        Deletes an object from this store.
        :param primary_key: Primary key of object to delete.
        :param delete_shards: Boolean to control whether shards are deleted.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: True if successful, False otherwise
        """
```

### DyObject API
```
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

    def save(self, primary_key=None, config_loader=None):
        """
        Saves this object to the store.
        :param primary_key: Primary key to use.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: key of object written
        """

    @classmethod
    def load(cls, primary_key, config_loader=None):
        """
        Loads an object from the store.
        :param cls: Class to instantiate
        :param primary_key: Primary key of object to load.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: cls object
        """
```