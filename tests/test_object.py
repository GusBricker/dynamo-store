from dynamo_store.store import DyStore
from dynamo_store.object import DyObject
import pytest
from uuid import uuid4
from copy import deepcopy
import sys

test_pk = ".".join([str(x) for x in sys.version_info[0:3]])

root_table_name = 'DynamoStoreRootDB'
root_key_name = 'ID'

@pytest.fixture
def root_store():
    geo_shard = [DyStore('DynamoStoreShard3Deep', 'ShardID', path='$.geolocation')]
    shards = [DyStore('DynamoStoreShard1', 'ID', path='$.birth_details'),
              DyStore('DynamoDBShard2', 'IDX', path='$.location', shards=geo_shard)]
    return DyStore(root_table_name, root_key_name, shards=shards)

@pytest.fixture
def base_item():
    d = {'firstname': 'john',
         'lastname': 'smith',
         'location': {'city': 'Osaka',
                      'country': 'Japan',
                      'geolocation': {'longitude': '90.00',
                                      'lattitude': '90.00'}},
         'birth_details': {'hospital': 'Kosei Nenkin',
                           'dob': '12/2/1995'}}
    return d

class GeoLocation(DyObject):
    TABLE_NAME = 'DynamoStoreShard3Deep'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ShardID'
    PATH = '$.geolocation'

    def __init__(self):
        self.longitude = None
        self.lattitude = None

class BirthDetails(DyObject):
    TABLE_NAME = 'DynamoStoreShard1'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    PATH = '$.birth_details'

    def __init__(self):
        self.hospital = None
        self.dob = None

class Location(DyObject):
    TABLE_NAME = 'DynamoDBShard2'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'IDX'
    PATH = '$.location'

    def __init__(self):
        self.city = None
        self.country = None
        self.geolocation = GeoLocation()

class Base(DyObject):
    TABLE_NAME = 'DynamoStoreRootDB'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    IGNORE_LIST = ['address']

    def __init__(self):
        self.firstname = None
        self.lastname = None
        self.location = Location()
        self.birth_details = BirthDetails()
        self.address = None

def loader1(config, data):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        encrypted_paths = ['birth_details.hospital', 'birth_details.dob', 'location.city', 'location.country', 'firstname', 'lastname']
        if data in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_GENERATE_PK:
        return test_pk
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def test_can_write_read_objects(root_store, base_item):
    orig = Base()
    orig.address = '123 fake st'
    orig.firstname = 'john'
    orig.lastname = 'smith'
    orig.location.city = 'Osaka'
    orig.location.country = 'Kewpie'
    orig.location.geolocation.lattitude = '99.1'
    orig.location.geolocation.longitude = '000.1'
    orig.birth_details.dob = '15/03/1980'
    orig.birth_details.hospital = 'Good one'
    key = orig.save(config_loader=loader1)

    o = Base.load(key, config_loader=loader1)
    assert o.address == None
    assert o.firstname == 'john'
    assert o.lastname == 'smith'
    assert isinstance(o.location, Location)
    assert o.location.city == 'Osaka'
    assert o.location.country == 'Kewpie'
    assert isinstance(o.location.geolocation, GeoLocation)
    assert o.location.geolocation.lattitude == '99.1'
    assert o.location.geolocation.longitude == '000.1'
    assert isinstance(o.birth_details, BirthDetails)
    assert o.birth_details.dob == '15/03/1980'
    assert o.birth_details.hospital == 'Good one'

def loader2(config, data):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        encrypted_paths = ['birth_details.hospital', 'birth_details.dob', 'location.city', 'location.country', 'firstname', 'lastname']
        if data in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_GENERATE_PK:
        return test_pk
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

def test_can_guess_objects(root_store, base_item):
    key = root_store.write(deepcopy(base_item), primary_key=test_pk, config_loader=loader2)
    assert key

    o = Base.load(key, config_loader=loader2)
    assert o.address == None
    assert o.firstname == 'john'
    assert o.lastname == 'smith'
    assert isinstance(o.location, Location)
    assert o.location.city == 'Osaka'
    assert o.location.country == 'Japan'
    assert isinstance(o.location.geolocation, GeoLocation)
    assert o.location.geolocation.lattitude == '90.00'
    assert o.location.geolocation.longitude == '90.00'
    assert isinstance(o.birth_details, BirthDetails)
    assert o.birth_details.dob == '12/2/1995'
    assert o.birth_details.hospital == 'Kosei Nenkin'

class BaseInternalLoader(DyObject):
    TABLE_NAME = 'DynamoStoreRootDB'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    IGNORE_LIST = ['address']
    CONFIG_LOADER = loader2

    def __init__(self):
        self.firstname = None
        self.lastname = None
        self.location = Location()
        self.birth_details = BirthDetails()
        self.address = None

def test_can_guess_objects_with_internal_loader(root_store, base_item):
    key = root_store.write(deepcopy(base_item), primary_key=test_pk)
    assert key

    o = BaseInternalLoader.load(key, config_loader=loader2)
    assert o.address == None
    assert o.firstname == 'john'
    assert o.lastname == 'smith'
    assert isinstance(o.location, Location)
    assert o.location.city == 'Osaka'
    assert o.location.country == 'Japan'
    assert isinstance(o.location.geolocation, GeoLocation)
    assert o.location.geolocation.lattitude == '90.00'
    assert o.location.geolocation.longitude == '90.00'
    assert isinstance(o.birth_details, BirthDetails)
    assert o.birth_details.dob == '12/2/1995'
    assert o.birth_details.hospital == 'Kosei Nenkin'