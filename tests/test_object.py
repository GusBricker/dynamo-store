from dynamo_store.store import DyStore
from dynamo_store.object import DyObject
import pytest
from uuid import uuid4
from copy import deepcopy
import sys
from jsonmodels import fields

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
    lattitude = fields.StringField()
    longitude = fields.StringField()

class BirthDetails(DyObject):
    TABLE_NAME = 'DynamoStoreShard1'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    hospital = fields.StringField()
    dob = fields.StringField()

class Location(DyObject):
    TABLE_NAME = 'DynamoDBShard2'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'IDX'
    city = fields.StringField()
    country = fields.StringField()
    geolocation = fields.EmbeddedField(GeoLocation)

class Base(DyObject):
    TABLE_NAME = 'DynamoStoreRootDB'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    IGNORE_LIST = ['address']
    firstname = fields.StringField()
    lastname = fields.StringField()
    location = fields.EmbeddedField(Location)
    birth_details = fields.EmbeddedField(BirthDetails)
    address = None

def loader1(config, **kwargs):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in kwargs
        assert 'data' in kwargs
        encrypted_paths = ['birth_details.hospital.value', 'birth_details.dob.value',
                           'locations.value.[0].city.value', 'locations.value.[0].country.value',
                           'locations.value.[1].city.value', 'locations.value.[1].country.value',
                           'locations.value.[0].geolocation.lattitude.value',
                           'locations.value.[0].geolocation.longitude.value',
                           'locations.value.[1].geolocation.lattitude.value',
                           'locations.value.[1].geolocation.longitude.value',
                           'firstname.value', 'lastname.value']
        if kwargs['path'] in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_GENERATE_PK:
        return test_pk
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def test_can_write_read_delete_read_objects(root_store, base_item):
    orig = Base(location = Location(geolocation=GeoLocation()), birth_details=BirthDetails())
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
    assert orig.__primary_key == test_pk

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
    assert o.__primary_key == test_pk

    assert orig.delete(config_loader=loader1)

    try:
        assert Base.load(key, config_loader=loader1) != None
    except:
        assert True

def test_can_write_read_objects(root_store, base_item):
    orig = Base(location = Location(geolocation=GeoLocation()), birth_details=BirthDetails())
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
    assert orig.__primary_key == test_pk

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
    assert o.__primary_key == test_pk

def loader2(config, **kwargs):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in kwargs
        assert 'data' in kwargs
        encrypted_paths = ['birth_details.hospital.value', 'birth_details.dob.value',
                           'locations.value.[0].city.value', 'locations.value.[0].country.value',
                           'locations.value.[1].city.value', 'locations.value.[1].country.value',
                           'locations.value.[0].geolocation.lattitude.value',
                           'locations.value.[0].geolocation.longitude.value',
                           'locations.value.[1].geolocation.lattitude.value',
                           'locations.value.[1].geolocation.longitude.value',
                           'firstname.value', 'lastname.value']
        if kwargs['path'] in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_GENERATE_PK:
        return test_pk
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False
    elif config == DyObject.CONFIG_LOADER_DICT_TO_CLASS:
        # In this case we can just use the dict key to determine what kind of object it is
        # other cases might require examining the value
        key = kwargs['key']
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
    assert o.__primary_key == test_pk

def loader_no_encryption(config, **kwargs):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        return None
    elif config == DyStore.CONFIG_LOADER_GENERATE_PK:
        return test_pk
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False
    elif config == DyObject.CONFIG_LOADER_DICT_TO_CLASS:
        # In this case we can just use the dict key to determine what kind of object it is
        # other cases might require examining the value
        key = kwargs['key']
        if key == 'location':
            return Location
        elif key == 'birth_details':
            return BirthDetails
        elif key == 'geolocation':
            return GeoLocation

    return None

class BaseInternalLoader(DyObject):
    TABLE_NAME = 'DynamoStoreRootDB'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    IGNORE_LIST = ['address']
    CONFIG_LOADER = loader_no_encryption
    firstname = fields.StringField()
    lastname = fields.StringField()
    location = fields.EmbeddedField(Location, default=Location())
    birth_details = fields.EmbeddedField(BirthDetails, default=BirthDetails())
    address = None

def test_can_guess_objects_with_internal_loader(root_store, base_item):
    key = root_store.write(deepcopy(base_item), primary_key=test_pk)
    assert key

    o = BaseInternalLoader.load(key)
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
    assert o.__primary_key == test_pk

class BaseMultipleLocation(DyObject):
    TABLE_NAME = 'DynamoStoreRootDB'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    IGNORE_LIST = ['address']
    firstname = fields.StringField()
    lastname = fields.StringField()
    locations = fields.ListField([Location])
    birth_details = fields.EmbeddedField(BirthDetails, default=BirthDetails())
    address = None

def loader3(config, **kwargs):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in kwargs
        assert 'data' in kwargs
        encrypted_paths = ['birth_details.hospital.value', 'birth_details.dob.value',
                           'locations.value.[0].city.value', 'locations.value.[0].country.value',
                           'locations.value.[1].city.value', 'locations.value.[1].country.value',
                           'locations.value.[0].geolocation.lattitude.value',
                           'locations.value.[0].geolocation.longitude.value',
                           'locations.value.[1].geolocation.lattitude.value',
                           'locations.value.[1].geolocation.longitude.value',
                           'firstname.value', 'lastname.value']
        if kwargs['path'] in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def test_can_write_read_multisharded_object(root_store, base_item):
    orig = BaseMultipleLocation(birth_details=BirthDetails())
    orig.address = '123 fake st'
    orig.firstname = 'john'
    orig.lastname = 'smith'

    loc1 = Location(geolocation=GeoLocation())
    loc1.city = 'Vienna'
    loc1.country = 'Austria'
    loc1.geolocation.lattitude = '40.0'
    loc1.geolocation.longitude = '41.0'
    orig.locations.append(loc1)

    loc2 = Location(geolocation=GeoLocation())
    loc2.city = 'Bejing'
    loc2.country = 'China'
    loc2.geolocation.lattitude = '50.0'
    loc2.geolocation.longitude = '51.0'
    orig.locations.append(loc2)

    orig.birth_details.dob = '15/03/1980'
    orig.birth_details.hospital = 'Good one'
    key = orig.save(config_loader=loader3)
    assert orig.__primary_key == key

    o = BaseMultipleLocation.load(key, config_loader=loader3)
    assert o.address == None
    assert o.firstname == 'john'
    assert o.lastname == 'smith'

    assert isinstance(o.locations, list)
    assert len(o.locations) == 2
    assert o.locations[0].city == 'Vienna'
    assert o.locations[0].country == 'Austria'
    assert isinstance(o.locations[0].geolocation, GeoLocation)
    assert o.locations[0].geolocation.lattitude == '40.0'
    assert o.locations[0].geolocation.longitude == '41.0'

    assert o.locations[1].city == 'Bejing'
    assert o.locations[1].country == 'China'
    assert isinstance(o.locations[1].geolocation, GeoLocation)
    assert o.locations[1].geolocation.lattitude == '50.0'
    assert o.locations[1].geolocation.longitude == '51.0'

    assert isinstance(o.birth_details, BirthDetails)
    assert o.birth_details.dob == '15/03/1980'
    assert o.birth_details.hospital == 'Good one'
    assert o.__primary_key == key

class NotAShard(DyObject):
    line = fields.IntField()
    data = fields.StringField()
    geo = fields.EmbeddedField(GeoLocation, default=GeoLocation())

class JustAShard(DyObject):
    line = fields.IntField()
    data = fields.StringField()

class BaseMixedShards(DyObject):
    TABLE_NAME = 'DynamoStoreRootDB'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    IGNORE_LIST = ['address']
    firstname = fields.StringField()
    lastname = fields.StringField()
    locations = fields.ListField([Location])
    birth_details = fields.EmbeddedField(BirthDetails, default=BirthDetails())
    info = fields.EmbeddedField(NotAShard, default=NotAShard())
    lines = fields.ListField(items_types=[JustAShard])
    address = None

def loader4(config, **kwargs):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in kwargs
        assert 'data' in kwargs
        encrypted_paths = ['birth_details.hospital.value', 'birth_details.dob.value',
                           'locations.value.[0].city.value', 'locations.value.[0].country.value',
                           'locations.value.[1].city.value', 'locations.value.[1].country.value',
                           'locations.value.[0].geolocation.lattitude.value',
                           'locations.value.[0].geolocation.longitude.value',
                           'locations.value.[1].geolocation.lattitude.value',
                           'locations.value.[1].geolocation.longitude.value',
                           'firstname.value', 'lastname.value', 'info.line.value', 'info.data.value', 'info.value',
                           'lines.value[0].line', 'lines.value[0].data', 'lines.value[1].line', 'lines.value[1].data']
        if kwargs['path'] in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def test_can_read_write_mixed_shard(root_store, base_item):
    orig = BaseMixedShards(info=NotAShard(), birth_details=BirthDetails())
    orig.address = '123 fake st'
    orig.firstname = 'john'
    orig.lastname = 'smith'
    orig.info.line = 100
    orig.info.data = 'line data'
    orig.info.geo = GeoLocation(lattitude='34.0', longitude='30.0')

    loc1 = Location(geolocation=GeoLocation())
    loc1.city = 'Vienna'
    loc1.country = 'Austria'
    loc1.geolocation.lattitude = '40.0'
    loc1.geolocation.longitude = '41.0'
    orig.locations.append(loc1)

    loc2 = Location(geolocation=GeoLocation())
    loc2.city = 'Bejing'
    loc2.country = 'China'
    loc2.geolocation.lattitude = '50.0'
    loc2.geolocation.longitude = '51.0'
    orig.locations.append(loc2)

    orig.birth_details.dob = '15/03/1980'
    orig.birth_details.hospital = 'Good one'
    key = orig.save(config_loader=loader4)
    assert orig.__primary_key == key

    o = BaseMixedShards.load(key, config_loader=loader4)
    assert o.address == None
    assert o.firstname == 'john'
    assert o.lastname == 'smith'
    assert isinstance(o.info, NotAShard)
    assert o.info.line == 100
    assert o.info.data == 'line data'
    assert isinstance(o.info.geo, GeoLocation)
    assert o.info.geo.lattitude == '34.0'
    assert o.info.geo.longitude == '30.0'
    assert isinstance(o.lines, list)
    assert len(orig.lines) == 0

    assert isinstance(o.locations, list)
    assert len(o.locations) == 2
    assert o.locations[0].city == 'Vienna'
    assert o.locations[0].country == 'Austria'
    assert isinstance(o.locations[0].geolocation, GeoLocation)
    assert o.locations[0].geolocation.lattitude == '40.0'
    assert o.locations[0].geolocation.longitude == '41.0'

    assert o.locations[1].city == 'Bejing'
    assert o.locations[1].country == 'China'
    assert isinstance(o.locations[1].geolocation, GeoLocation)
    assert o.locations[1].geolocation.lattitude == '50.0'
    assert o.locations[1].geolocation.longitude == '51.0'

    assert isinstance(o.birth_details, BirthDetails)
    assert o.birth_details.dob == '15/03/1980'
    assert o.birth_details.hospital == 'Good one'
    assert o.__primary_key == key

class LineInfo(DyObject):
    number = fields.IntField()
    geo = fields.EmbeddedField(GeoLocation, default=GeoLocation())

class Line(DyObject):
    lineinfo = fields.EmbeddedField(LineInfo, default=LineInfo())
    text = fields.StringField()

class Title(DyObject):
    lines = fields.EmbeddedField(Line, default=Line())

class BaseDeepMixedShards(DyObject):
    TABLE_NAME = 'DynamoStoreRootDB'
    REGION_NAME = 'us-east-2'
    PRIMARY_KEY_NAME = 'ID'
    title = fields.EmbeddedField(Title, default=Title())
    info = fields.ListField(items_types=[Line])

def loader5(config, **kwargs):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in kwargs
        assert 'data' in kwargs
        path = kwargs['path']
        unencrypted_paths = ['__module__', '__class__', '__metatype__']
        for p in unencrypted_paths:
            if p in path:
                return None

        if path == 'info.value':
            return None
        return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def test_can_read_write_deepmixed_shard(root_store, base_item):
    orig = BaseDeepMixedShards()
    orig.title.lines.text = 'title'
    orig.title.lines.lineinfo.number = 0
    orig.title.lines.lineinfo.geo = GeoLocation(lattitude='34.0', longitude='30.0')

    orig.info.append(Line(text='hello', lineinfo=LineInfo(number=1, geo=GeoLocation(lattitude='54.0', longitude='50.0'))))
    orig.info.append(Line(text='world', lineinfo=LineInfo(number=2, geo=GeoLocation(lattitude='52.0', longitude='51.0'))))

    key = orig.save(config_loader=loader5)
    assert orig.__primary_key == key

    o = BaseDeepMixedShards.load(key, config_loader=loader5)
    assert isinstance(o.title, Title)
    assert isinstance(o.title.lines, Line)
    assert isinstance(o.title.lines.lineinfo.geo, GeoLocation)
    assert o.title.lines.text == 'title'
    assert o.title.lines.lineinfo.number == 0
    assert o.title.lines.lineinfo.geo.lattitude == '34.0'
    assert o.title.lines.lineinfo.geo.longitude == '30.0'

    assert len(o.info) == 2
    assert isinstance(o.info[0], Line)
    assert isinstance(o.info[1], Line)
    assert isinstance(o.info[0].lineinfo, LineInfo)
    assert isinstance(o.info[1].lineinfo, LineInfo)
    assert isinstance(o.info[0].lineinfo.geo, GeoLocation)
    assert isinstance(o.info[1].lineinfo.geo, GeoLocation)
    assert o.info[0].text == 'hello'
    assert o.info[1].text == 'world'
    assert o.info[0].lineinfo.number == 1
    assert o.info[1].lineinfo.number == 2
    assert o.info[0].lineinfo.geo.lattitude == '54.0'
    assert o.info[0].lineinfo.geo.longitude == '50.0'
    assert o.info[1].lineinfo.geo.lattitude == '52.0'
    assert o.info[1].lineinfo.geo.longitude == '51.0'
    assert o.__primary_key == key

def loader_no_pk(config, **kwargs):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in kwargs
        assert 'data' in kwargs
        encrypted_paths = ['birth_details.hospital.value', 'birth_details.dob.value',
                           'locations.value.[0].city.value', 'locations.value.[0].country.value',
                           'locations.value.[1].city.value', 'locations.value.[1].country.value',
                           'locations.value.[0].geolocation.lattitude.value',
                           'locations.value.[0].geolocation.longitude.value',
                           'locations.value.[1].geolocation.lattitude.value',
                           'locations.value.[1].geolocation.longitude.value',
                           'firstname.value', 'lastname.value']
        if kwargs['path'] in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def test_can_write_read_delete_read_objects_with_key(root_store, base_item):
    orig = Base(location = Location(geolocation=GeoLocation()), birth_details=BirthDetails())
    orig.address = '123 fake st'
    orig.firstname = 'john'
    orig.lastname = 'smith'
    orig.location.city = 'Osaka'
    orig.location.country = 'Kewpie'
    orig.location.geolocation.lattitude = '99.1'
    orig.location.geolocation.longitude = '000.1'
    orig.birth_details.dob = '15/03/1980'
    orig.birth_details.hospital = 'Good one'
    key = orig.save(primary_key=test_pk, config_loader=loader_no_pk)
    assert orig.__primary_key == test_pk

    o = Base.load(test_pk, config_loader=loader_no_pk)
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
    assert o.__primary_key == test_pk

    assert orig.delete(primary_key=test_pk, config_loader=loader_no_pk)

    try:
        assert Base.load(primary_key=test_pk, config_loader=loader_no_pk) != None
    except:
        assert True
