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
