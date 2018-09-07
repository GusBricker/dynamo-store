import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from dynamo_store.log import logger
from dynamo_store.aescrypt import AESCipher
from dynamo_store import util
from jsonpath_ng import jsonpath, parse
from uuid import uuid4
from datetime import datetime

class DyStore(object):
    METADATA_KEY = '__dystore_meta__'

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
        if table_name and region:
            dynamodb = boto3.resource("dynamodb", region_name=region)
            self.region = region
            self.table = dynamodb.Table(table_name)
        self._primary_key_name = primary_key_name
        self._shards = shards
        self.path = path

    @staticmethod
    def from_dict(obj, d):
        shards = []
        for s in d.get('shards', []):
            shard_obj = DyStore()
            DyStore.from_dict(shard_obj, s)
            shards.append(shard_obj)
        
        obj.region = d['region_name']
        dynamodb = boto3.resource("dynamodb", region_name=obj.region)
        obj.table = dynamodb.Table(d['table_name'])
        obj._primary_key_name = d['primary_key_name']
        obj.path = d['path']
        obj._shards = shards

    def to_dict(self):
        shards = []
        for s in self._shards:
            shards.append(s.to_dict())

        return {'table_name': self.table.name,
                'region_name': self.region,
                'primary_key_name': self._primary_key_name,
                'path': self.path,
                'shards': shards}

    def _try_invoke_config_loader(self, loader, config, data):
        if loader and callable(loader):
            return loader(config, data)
        return None

    def _decrypt(self, root_object, config_loader):
        if not config_loader or not callable(config_loader):
            return

        for encrypted_value in util.generate_paths(root_object):
            path = str(encrypted_value.full_path)
            key = config_loader(DyStore.CONFIG_LOADER_LOAD_KEY, {'path': path, 'root': root_object})
            if key:
                cipher = AESCipher(key)
                json_path = parse(path)
                logger.debug('Decrypting item: %s' % path)
                unencrypted_value = cipher.decrypt(encrypted_value.value)
                logger.debug('Decrypted item: %s' % path)
                logger.debug('Before: %s' % root_object)
                json_path.update(root_object, unencrypted_value)
                logger.debug('After: %s' % root_object)

    def _encrypt(self, root_object, config_loader):
        if not config_loader or not callable(config_loader):
            return
        for unencrypted_value in util.generate_paths(root_object):
            path = str(unencrypted_value.full_path)
            key = config_loader(DyStore.CONFIG_LOADER_LOAD_KEY, {'path': path, 'root': root_object})
            if key:
                cipher = AESCipher(key)
                json_path = parse(path)
                logger.debug('Encrypting item: %s' % path)
                encrypted_value = cipher.encrypt(unencrypted_value.value)
                logger.debug('Encrypted item: %s' % path)
                logger.debug('Before: %s' % root_object)
                json_path.update(root_object, encrypted_value)
                logger.debug('After: %s' % root_object)

    def _shard_from_metadata(self, metadata):
        return metadata['primary_key']

    def _resolve_shards(self, item, config_loader, root_object, shard_path):
        for shard in self._shards:
            json_path = parse(shard.path)
            for shard_meta in json_path.find(item):
                if shard_meta:
                    primary_key = self._shard_from_metadata(shard_meta.value)
                    if shard_path:
                        p = shard_path + '.' + util.remove_prefix(shard.path, '$.')
                    else:
                        p = shard.path
                    success, shard_value = shard._read(primary_key, config_loader=config_loader, root_object=root_object, shard_path=p)
                    if success:
                        if not parse(str(shard_meta.full_path)).update(item, shard_value):
                            return False
                        logger.debug('Successfully resolved shard %s: %s' % (p, shard_meta))
                    else:
                        logger.error('Failed to resolve shard %s' % shard_meta)
                        return False

        return True

    def _shard_to_metadata(self, shard_key, shard):
        return {'primary_key': shard_key,
                'table_name:': shard.table.name,
                'region_name:': shard.region,
                'modified_utc': datetime.utcnow().strftime("%s")}

    def _save_shards(self, item, config_loader, root_object, shard_path):
        for shard in self._shards:
            json_path = parse(shard.path)
            for shard_value in json_path.find(item):
                if shard_value:
                    if shard_path:
                        p = shard_path + '.' + util.remove_prefix(shard.path, '$.')
                    else:
                        p = shard.path
                    shard_key = shard._write(shard_value.value, config_loader=config_loader, root_object=root_object, shard_path=p)
                    if shard_key:
                        metadata = self._shard_to_metadata(shard_key, shard)
                        if not parse(str(shard_value.full_path)).update(item, metadata):
                            return False
                        logger.debug('Successfully saved shard %s: %s' % (p, shard_key))
                    else:
                        logger.error('Failed to save shard %s' % shard_key)
                        return False

        return True

    def _delete_shards(self, item, config_loader):
        for shard in self._shards:
            json_path = parse(shard.path)
            for shard_key in json_path.find(item):
                if shard_key:
                    primary_key = self._shard_from_metadata(shard_key.value)
                    if shard.delete(primary_key, config_loader=config_loader):
                        logger.debug('Successfully deleted shard %s' % shard_key)
                    else:
                        logger.error('Failed to delete shard %s' % shard_key)
                        return False

        return True


    def read_path(self, primary_key, path, config_loader=None):
        """
        Reads a path from an object from this store.
        :param primary_key: Primary key of object to read.
        :param path: JSON path of object to read (can reside in a shard).
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: list of values on success, None otherwise
        """
        logger.debug('Writing path: %s: %s' % (primary_key, path))
        success, data = self.read(primary_key, config_loader=config_loader)
        if not success:
            return None

        expr = parse(path)
        values = expr.find(data)
        if not values:
            return None

        return [x.value for x in values]

    def _read(self, primary_key, resolve_shards=True, config_loader=None, root_object=None, shard_path=None):
        """
        Reads an object from this store.
        :param primary_key: Primary key of object to read.
        :param resolve_shards: Boolean to control whether shards are read.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting.
        :param root_object: Internal parameter used for proper path resolution in config load calls.
        :returns: success, value
        """
        key = {self._primary_key_name: primary_key}
        logger.debug('Reading: %s' % key)

        try:
            response = self.table.get_item(Key=key)
        except ClientError as e:
            logger.error (e.response['Error']['Message'])
            return False, {}

        if 'Item' in response:
            item = response['Item']
            if root_object == None:
                root_object = item

            if shard_path:
                if not parse(shard_path).update(root_object, item):
                    return False, {}
            
            DyStore.from_dict(self, item[DyStore.METADATA_KEY])

            if resolve_shards:
                if not self._resolve_shards(item, config_loader, root_object, shard_path):
                    return False, {}

            if self._try_invoke_config_loader(config_loader, DyStore.CONFIG_LOADER_KEEP_METADATA, item) == False:
                del item[self._primary_key_name]
                del item[DyStore.METADATA_KEY]

            logger.debug('Read: %s' % key)
            return True, item

        return False, {}

    def read(self, primary_key, resolve_shards=True, config_loader=None):
        """
        Reads an object from this store.
        :param primary_key: Primary key of object to read.
        :param resolve_shards: Boolean to control whether shards are read.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: success, value
        """
        success, item = self._read(primary_key, resolve_shards=resolve_shards, config_loader=config_loader)

        if success:
            self._decrypt(item, config_loader)

        return success, item

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
        logger.debug('Writing path: %s: %s' % (primary_key, path))
        success, data = self.read(primary_key, config_loader=config_loader)
        if not success:
            return False

        expr = parse(path)
        if not expr.find(data):
            return False

        expr.update(data, value)

        if not self.write(data, primary_key=primary_key, config_loader=config_loader):
            return False

        logger.debug('Writen path: %s: %s' % (primary_key, path))
        return True

    def _write(self, data, primary_key=None, save_shards=True, config_loader=None, root_object=None, shard_path=None):
        """
        Writes an object to this store.
        :param primary_key: Primary key of object to write.
        :param save_shards: Boolean to control whether shards are saved.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: primary_key used/generated
        """
        data[DyStore.METADATA_KEY] = self.to_dict()

        if not primary_key:
            if config_loader and callable(config_loader):
                primary_key = config_loader(DyStore.CONFIG_LOADER_GENERATE_PK, data)
            if not primary_key:
                primary_key = str(uuid4())

        key = {self._primary_key_name: primary_key}
        data.setdefault(self._primary_key_name, primary_key)
        logger.debug('Writing: %s' % key)
        logger.debug('Save Shards: %s' % save_shards)

        if not root_object:
            root_object = data

        if not self._save_shards(data, config_loader, root_object, shard_path):
            return None

        try:
            self.table.put_item(Item=data)
        except ClientError as e:
            logger.error(e.response['Error']['Message'])
            return None

        if self._try_invoke_config_loader(config_loader, DyStore.CONFIG_LOADER_KEEP_METADATA, data) == False:
            del data[DyStore.METADATA_KEY]
            del data[self._primary_key_name]

        logger.debug('Writen: %s' % key)
        return primary_key

    def write(self, data, primary_key=None, save_shards=True, config_loader=None):
        """
        Writes an object to this store.
        :param primary_key: Primary key of object to write.
        :param save_shards: Boolean to control whether shards are saved.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: primary_key used/generated
        """
        self._encrypt(data, config_loader)

        return self._write(data, primary_key=primary_key, save_shards=save_shards, config_loader=config_loader)

    def delete(self, primary_key, delete_shards=True, config_loader=None):
        """
        Deletes an object from this store.
        :param primary_key: Primary key of object to delete.
        :param delete_shards: Boolean to control whether shards are deleted.
        :param config_loader: Config loader to be used: config_loader(config, data) returns setting
        :returns: True if successful, False otherwise
        """
        key = {self._primary_key_name: primary_key}
        logger.debug('Deleting: %s' % key)

        success, item = self.read(primary_key, resolve_shards=False, config_loader=config_loader) 
        if not success:
            return False

        if delete_shards:
            if not self._delete_shards(item, config_loader):
                return False

        try:
            self.table.delete_item(Key=key, ReturnValues='NONE')
        except ClientError as e:
            logger.error (e.response['Error']['Message'])
            return False

        logger.debug('Deleted: %s' % key)
        return True
