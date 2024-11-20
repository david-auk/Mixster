class Cache:
    __data = {}

    @staticmethod
    def has_attribute(attribute: str):
        if attribute in Cache.__data:
            return True

        return False

    @staticmethod
    def has_key(attribute: str, key: str):
        if Cache.has_attribute(attribute):
            if key in Cache.__data[attribute]:
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def add(attribute: str, key: str, value):
        if Cache.has_key(attribute, key):
            raise RuntimeError("Key already exists")

        if not Cache.has_attribute(attribute):
            Cache.__data[attribute] = {}

        Cache.__data[attribute][key] = value

    @staticmethod
    def get(attribute: str, key: str):
        if not Cache.has_key(attribute, key):
            raise RuntimeError("Key not found")

        return Cache.__data[attribute][key]

    @staticmethod
    def remove(attribute: str, key: str):
        if not Cache.has_key(attribute, key):
            raise RuntimeError("Key not found")

        del Cache.__data[attribute][key]
