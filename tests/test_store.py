from dynamo_store.store import DyStore
import pytest
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

@pytest.fixture
def complex_item():
    d = {'firstname': 'john',
         'lastname': 'smith',
         'location': {'city': 'Osaka',
                      'country': 'Japan',
                      'geolocation': {'longitude': '90.00',
                                      'lattitude': '90.00'}},
         'birth_details': {'hospital': 'Kosei Nenkin',
                           'dob': '12/2/1995'},
         'friends': ['bob',
                     'john',
                     'mick'],
         'locales': [{'type': 'en_US'},
                     {'type': 'en_IE'},
                     {'type': 'nl_NL'}]}
    return d

def loader(config, data):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in data
        assert 'root' in data
        encrypted_paths = ['birth_details.hospital', 'birth_details.dob', 'location.city', 'location.country', 'firstname', 'lastname']
        if data['path'] in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_GENERATE_PK:
        return test_pk
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def loader_full_encryption(config, data):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in data
        assert 'root' in data
        encrypted_paths = ['birth_details.hospital', 'birth_details.dob', 'location.city', 'location.country',
                           'firstname', 'lastname', 'location.geolocation.longitude', 'location.geolocation.lattitude',
                           'friends', 'locales.[0].type', 'locales.[1].type', 'locales.[2].type']
        if data['path'] in encrypted_paths:
            return '123kgk132l'
    elif config == DyStore.CONFIG_LOADER_GENERATE_PK:
        return test_pk
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def loader_no_encryption(config, data):
    if config == DyStore.CONFIG_LOADER_LOAD_KEY:
        assert 'path' in data
        assert 'root' in data
    elif config == DyStore.CONFIG_LOADER_GENERATE_PK:
        return test_pk
    elif config == DyStore.CONFIG_LOADER_KEEP_METADATA:
        return False

    return None

def test_encryption(root_store, complex_item):
    key = root_store.write(deepcopy(complex_item), primary_key=test_pk, config_loader=loader_full_encryption)
    assert key

    success, readback = root_store.read(key, config_loader=loader_no_encryption)
    assert success

    print('--READ BACK--')
    print(readback)
    print('--BASE ITEM--')
    print(complex_item)

    from boto3.dynamodb.types import Binary
    assert readback != base_item
    assert isinstance(readback['firstname'], Binary)
    assert readback['firstname'] != complex_item['firstname']

    assert isinstance(readback['lastname'], Binary)
    assert readback['lastname'] != complex_item['lastname']

    assert isinstance(readback['location']['city'], Binary)
    assert readback['location']['city'] != complex_item['location']['city']

    assert isinstance(readback['location']['country'], Binary)
    assert readback['location']['country'] != complex_item['location']['country']

    assert isinstance(readback['location']['geolocation']['lattitude'], Binary)
    assert readback['location']['geolocation']['lattitude'] != complex_item['location']['geolocation']['lattitude']

    assert isinstance(readback['location']['geolocation']['longitude'], Binary)
    assert readback['location']['geolocation']['longitude'] != complex_item['location']['geolocation']['longitude']

    assert isinstance(readback['birth_details']['hospital'], Binary)
    assert readback['birth_details']['hospital'] != complex_item['birth_details']['hospital']

    assert isinstance(readback['birth_details']['dob'], Binary)
    assert readback['birth_details']['dob'] != complex_item['birth_details']['dob']

    assert isinstance(readback['friends'], Binary)
    assert readback['friends'] != complex_item['friends']

    assert len(readback['locales']) == 3
    assert readback['locales'][0]['type'] != complex_item['locales'][0]['type']
    assert readback['locales'][1]['type'] != complex_item['locales'][1]['type']
    assert readback['locales'][2]['type'] != complex_item['locales'][2]['type']

    assert root_store.delete(key, config_loader=loader_full_encryption)

def test_write_read_delete(root_store, base_item):
    key = root_store.write(deepcopy(base_item), primary_key=test_pk, config_loader=loader)
    assert key

    success, readback = root_store.read(key, config_loader=loader)
    assert success

    print('--READ BACK--')
    print(readback)
    print('--BASE ITEM--')
    print(base_item)

    assert readback == base_item

    assert root_store.delete(key, config_loader=loader)

def test_write_anon_read_delete(root_store, base_item):
    key = root_store.write(deepcopy(base_item), primary_key=test_pk, config_loader=loader)
    assert key

    success, readback = DyStore(table_name=root_table_name, primary_key_name=root_key_name).read(key, config_loader=loader)
    assert success

    print('--READ BACK--')
    print(readback)
    print('--BASE ITEM--')
    print(base_item)

    assert readback == base_item

    assert DyStore(table_name=root_table_name, primary_key_name=root_key_name).delete(key, config_loader=loader)

def test_write_read_path(root_store, base_item):
    key = root_store.write(deepcopy(base_item), primary_key=test_pk, config_loader=loader)
    assert key

    assert root_store.read_path(key, '$.lastname', config_loader=loader) == ['smith']
    assert root_store.write_path(key, '$.lastname', 'walter', config_loader=loader)
    assert root_store.read_path(key, '$.lastname', config_loader=loader) == ['walter']

    assert root_store.read_path(key, '$.location.city', config_loader=loader) == ['Osaka']
    assert root_store.write_path(key, '$.location.city', 'Tokyo', config_loader=loader)
    assert root_store.read_path(key, '$.location.city', config_loader=loader) == ['Tokyo']

    assert root_store.read_path(key, '$.location.geolocation.longitude', config_loader=loader) == ['90.00']
    assert root_store.write_path(key, '$.location.geolocation.longitude', '-90.00', config_loader=loader)
    assert root_store.read_path(key, '$.location.geolocation.longitude', config_loader=loader) == ['-90.00']
