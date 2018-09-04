from dynamo_store import util
from dynamo_store.log import logger
import pytest

def test_remove_prefix():
    assert util.remove_prefix('testing', 'test') == 'ing'
    assert util.remove_prefix('testing', '2test') == 'testing'
    assert util.remove_prefix('testtesting', 'test') == 'testing'
    assert util.remove_prefix('ing', 'test') == 'ing'
    assert util.remove_prefix('', 'test') == ''
    assert util.remove_prefix(' space', ' ') == 'space'
    assert util.remove_prefix(' space ', ' ') == 'space '

def test_generate_empty_dict_paths():
    d = {}
    p = [str(x.full_path) for x in util.generate_paths(d, None)]
    logger.debug(p)
    assert len(p) == 0

def test_generate_first_level_list_paths():
    d = {'firstname': 'john',
         'lastname': 'smith',
         'locations': [{'city': 'Osaka', 'country': 'Japan'},
                       {'city': 'Bejing', 'country': 'China'}]}
    p = [str(x.full_path) for x in util.generate_paths(d, 'locations')]
    logger.debug(p)
    assert len(p) == 4
    assert 'locations.[0].city' in p
    assert 'locations.[0].country' in p
    assert 'locations.[1].city' in p
    assert 'locations.[1].country' in p

def test_generate_second_level_list_paths():
    d = {'firstname': 'john',
         'lastname': 'smith',
         'person': { 'locations': [{'city': 'Osaka', 'country': 'Japan'},
                                   {'city': 'Bejing', 'country': 'China'}]}}
    p = [str(x.full_path) for x in util.generate_paths(d, 'person.locations')]
    logger.debug(p)
    assert len(p) == 4
    assert 'person.locations.[0].city' in p
    assert 'person.locations.[0].country' in p
    assert 'person.locations.[1].city' in p
    assert 'person.locations.[1].country' in p

def test_generate_second_level_non_dict_list_paths():
    d = {'firstname': 'john',
         'lastname': 'smith',
         'person': { 'locations': ['Japan', 'Africa']}},
    p = [str(x.full_path) for x in util.generate_paths(d, 'person.locations')]
    logger.debug(p)
    assert len(p) == 0

def test_generate_second_level_paths():
    d = {'firstname': 'john',
         'lastname': 'smith',
         'location': {'city': 'Osaka',
                      'country': 'Japan',
                      'geolocation': {'longitude': '90.00',
                                      'lattitude': '90.00'}},
         'birth_details': {'hospital': 'Kosei Nenkin',
                           'dob': '12/2/1995'}}
    p = [str(x.full_path) for x in util.generate_paths(d, 'location.geolocation')]
    logger.debug(p)
    assert len(p) == 2
    assert 'location.geolocation.longitude' in p
    assert 'location.geolocation.lattitude' in p

def test_generate_first_level_paths():
    d = {'firstname': 'john',
         'lastname': 'smith',
         'location': {'city': 'Osaka',
                      'country': 'Japan',
                      'geolocation': {'longitude': '90.00',
                                      'lattitude': '90.00'}},
         'birth_details': {'hospital': 'Kosei Nenkin',
                           'dob': '12/2/1995'}}
    p = [str(x.full_path) for x in util.generate_paths(d, '$.location')]
    logger.debug(p)
    assert len(p) == 2
    assert 'location.city' in p
    assert 'location.country' in p

def test_generate_root_paths():
    d = {'firstname': 'john',
         'lastname': 'smith',
         'location': {'city': 'Osaka',
                      'country': 'Japan',
                      'geolocation': {'longitude': '90.00',
                                      'lattitude': '90.00'}},
         'birth_details': {'hospital': 'Kosei Nenkin',
                           'dob': '12/2/1995'}}
    p = [str(x.full_path) for x in util.generate_paths(d, None)]
    logger.debug(p)
    assert len(p) == 2
    assert 'firstname' in p
    assert 'lastname' in p
