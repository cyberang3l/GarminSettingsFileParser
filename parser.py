import io
import json
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast
)


class SettingString(str):
    def __init__(self, input: Union[str, io.BufferedIOBase], advanceSeek: bool = True):
        if isinstance(input, io.BufferedIOBase):
            seekBefore = input.tell()
            [strLen] = struct.unpack('>H', input.read(2))
            self.string: str = input.read(strLen).decode('ascii').rstrip('\x00')
            if not advanceSeek:
                input.seek(seekBefore)
            return

        assert isinstance(input, str), f"input must be a string or a BufferedIOBase - got {type(input)}"
        try:
            input.encode('ascii')
            self.string: str = input.rstrip('\x00')
        except UnicodeEncodeError as e:
            raise UnicodeEncodeError('ascii', input, 0, len(input), f"Not a valid ASCII string: {input}") from e

    @property
    def size(self) -> int:
        return len(self.bytes)

    @property
    def strlen(self) -> int:
        return len(self.string) + 1  # +1 for the null terminator

    @property
    def bytes(self) -> bytes:
        return struct.pack('>H', self.strlen) + self.string.encode('ascii') + b'\x00'

    def __len__(self) -> int:
        return self.strlen

    def __str__(self) -> str:
        return self.string

    def __repr__(self) -> str:
        return f"{self.string}-len({self.strlen})"

    def __hash__(self) -> int:
        return hash(self.string + "randomButNotSoRandomButHardEnoughToCauseACollisionInSaneUsageStringToMakeHash")

    def __eq__(self, other: object) -> bool:
        if type(other) is SettingString:
            return self.string == other.string
        return False

    def __ne__(self, other) -> bool:
        return not (self == other)


class SettingStringTable:
    def __init__(self, input: Optional[Union[List[SettingString], io.BufferedIOBase]] = None, advanceSeek: bool = True):
        self._strings: List[SettingString] = []
        self._index_to_string: Dict[int, SettingString] = {}
        self._string_to_index: Dict[SettingString, int] = {}
        self._next_index = 0

        if input is None:
            return

        if isinstance(input, io.BufferedIOBase):
            seekBefore = input.tell()
            [tableLen] = struct.unpack('>I', input.read(4))

            afterTableLen = input.tell()
            sizeTillEOF = len(input.read())
            input.seek(afterTableLen)

            if tableLen > sizeTillEOF:
                raise ValueError("Binary file dot not contain a valid string table - "
                                 f"Expecting at least {tableLen} bytes, got {sizeTillEOF} bytes")

            size = 0
            while size < tableLen:
                string = SettingString(input)
                size += string.size
                self._strings.append(string)

            if not advanceSeek:
                input.seek(seekBefore)

            self.__init__(self._strings)
            return

        assert isinstance(input, list), f"input must be a list or a BufferedIOBase - got {type(input)}"
        for s in input:
            if s in self._string_to_index:
                continue
            self._strings.append(s)
            self._string_to_index[s] = self._next_index
            self._index_to_string[self._next_index] = s
            self._next_index += s.size

    @property
    def size(self) -> int:
        size = sum(s.size for s in self._strings)
        assert self._next_index == size, f"self._next_index ({self._next_index}) != size ({size})"
        return size

    def _bytesOnlyStringTable(self) -> bytes:
        return b''.join(s.bytes for s in self._strings)

    @property
    def bytes(self) -> bytes:
        return struct.pack('>I', self.size) + self._bytesOnlyStringTable()

    def __getitem__(self, key: Union[SettingString, int]) -> Union[int, SettingString]:
        if isinstance(key, SettingString):
            return self._string_to_index[key]
        return self._index_to_string[key]

    def __delitem__(self, key: Union[SettingString, int]):
        self.remove(key)

    def __iter__(self) -> Iterator[SettingString]:
        return iter(self._strings)

    def __contains__(self, key: Union[SettingString, int]) -> bool:
        if type(key) is SettingString:
            return key in self._string_to_index
        return key in self._index_to_string

    def __repr__(self) -> str:
        return str(self._strings)

    def __len__(self) -> int:
        return len(self._strings)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SettingStringTable):
            return set(self._strings) == set(other._strings)
        return False

    def __ne__(self, other) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        hash_string = ""
        for s in self._strings:
            hash_string += str(hash(s))
        return hash(hash_string)

    def items(self, key_is_string: bool = True) -> Iterable[Union[tuple[SettingString, int], tuple[int, SettingString]]]:
        if key_is_string:
            return self._string_to_index.items()
        return self._index_to_string.items()

    def has_key(self, key: Union[SettingString, int]) -> bool:
        return key in self

    def remove(self, key: Union[SettingString, int]):
        if isinstance(key, int):
            key = self._index_to_string[key]

        self._strings.remove(key)
        self.__init__(self._strings)

    def add(self, s: SettingString):
        """
        Add a string to the table if it doesn't already exist
        """
        if s in self._string_to_index:
            return
        self._strings.append(s)
        self._string_to_index[s] = self._next_index
        self._index_to_string[self._next_index] = s
        self._next_index += s.size


class PropertyType(IntEnum):
    INT32 = 0x01
    FLOAT32 = 0x02
    STRING = 0x03
    BOOLEAN = 0x09
    LONG64 = 0x0E
    DOUBLE64 = 0x0F


def getPropertyTypeStructPack(type: PropertyType) -> Tuple[int, str, type]:
    if type == PropertyType.INT32:
        return 4, '>i', int
    elif type == PropertyType.FLOAT32:
        return 4, '>f', float
    elif type == PropertyType.STRING:
        return 4, '>I', SettingString
    elif type == PropertyType.BOOLEAN:
        return 1, '?', bool
    elif type == PropertyType.LONG64:
        return 8, '>q', int
    elif type == PropertyType.DOUBLE64:
        return 8, '>d', float
    raise ValueError(f"Unknown property type: {type}")


def getPropertyTypeFromString(s: str) -> PropertyType:
    if s == "number":
        return PropertyType.INT32
    elif s == "float":
        return PropertyType.FLOAT32
    elif s == "string":
        return PropertyType.STRING
    elif s == "boolean":
        return PropertyType.BOOLEAN
    elif s == "long":
        return PropertyType.LONG64
    elif s == "double":
        return PropertyType.DOUBLE64
    raise ValueError(f"Unknown property type: {s}")


@dataclass
class Property:
    name: SettingString
    type: PropertyType
    value: Union[SettingString, bool, int, float]

    def bytes(self, stringTable: SettingStringTable) -> bytes:
        _, packPropertyName, _ = getPropertyTypeStructPack(PropertyType.STRING)
        assert self.name in stringTable, f"Property name '{self.name}' not in string table - cannot serialize property"

        _, packPropertyValue, _ = getPropertyTypeStructPack(self.type)

        propertyBytes = struct.pack('>b', self.type.value)
        if self.type == PropertyType.STRING:
            assert type(self.value) is SettingString
            assert self.value in stringTable, f"String property value '{self.value}' not in string table - cannot serialize property"
            propertyBytes += struct.pack(packPropertyValue, stringTable[self.value])
        else:
            propertyBytes += struct.pack(packPropertyValue, self.value)

        return struct.pack('>b', PropertyType.STRING) + \
            struct.pack(packPropertyName, stringTable[self.name]) + \
            propertyBytes


def parsePropertyFromBinary(f: io.BufferedIOBase, stringTable: SettingStringTable) -> Property:
    # Each property starts with a string that is the property name
    [propertyType] = struct.unpack('>B', f.read(1))
    propertyType = PropertyType(propertyType)
    assert propertyType == PropertyType.STRING, f"Expected property type {PropertyType.STRING} to get the Property ID (or property name) but got {propertyType}"
    numBytes, packPropertyName, _ = getPropertyTypeStructPack(propertyType)
    [propertyNameIndex] = struct.unpack(packPropertyName, f.read(numBytes))
    assert propertyNameIndex in stringTable, f"Property name index '{propertyNameIndex}' not in string table - cannot parse property"
    propertyId = stringTable[propertyNameIndex]
    assert type(propertyId) is SettingString

    # Then the property value type and value follows
    [propertyValueType] = struct.unpack('>B', f.read(1))
    propertyValueType = PropertyType(propertyValueType)
    [numBytes, packPropertyValue, pythonValueType] = getPropertyTypeStructPack(propertyValueType)
    if pythonValueType is SettingString:
        [propertyValueIndex] = struct.unpack(packPropertyValue, f.read(numBytes))
        assert propertyValueIndex in stringTable, f"Property value index '{propertyValueIndex}' not in string table - cannot parse property"
        propertyValue = stringTable[propertyValueIndex]
    else:
        [propertyValue] = struct.unpack(packPropertyValue, f.read(numBytes))

    return Property(name=propertyId, type=propertyValueType, value=propertyValue)


# Min file size is start value (4 bytes) + mid value (4 bytes) + 4 bytes indicating
# the size of the string table and 4 bytes indicating the size of the property values
MIN_FILE_SIZE = 16
MAGIC_VALUES_BYTE_SIZE = 4
START_OF_FILE_MAGIC_VALUE = 0xABCDABCD
MID_OF_FILE_MAGIC_VALUE = 0xDA7ADA7A
FIXED_VALUE_AFTER_MID_OF_FILE = 0x0B
LEN_FIELD_SIZE = 2
NULL_TERMINATOR_SIZE = 1
START_OF_PROPERTY_IDS_INDEX = 8


####### <------- IMPLEMENT THIS -------> #######
# When reading from binary file, first build a SettingStringTable, then read the properties
# When reading from JSON file, the properties first and then generate the SettingStringTable
class GarminProperties:
    def _parsePropertiesFromJsonFile(self, f: io.BufferedIOBase):
        settingJson = json.loads(f.read())
        assert isinstance(settingJson, dict), "Garmin-settings.json must be a JSON object with a dict"
        assert "settings" in settingJson, "Garmin-settings.json must contain a 'settings' key"
        assert isinstance(settingJson["settings"], list), "Garmin-settings.json settings must be a list"
        for prop in settingJson["settings"]:
            assert isinstance(prop, dict), "Garmin-settings.json settings must be a list of dicts"
            assert "key" in prop, "Garmin-settings.json must constain a 'settings' key"
            assert "valueType" in prop, "Garmin-settings.json settings must contain a 'valueType' key"
            assert "defaultValue" in prop, "Garmin-settings.json settings must contain a 'defaultValue' key"
            propertyType = getPropertyTypeFromString(prop["valueType"])
            _, _, internalPythonType = getPropertyTypeStructPack(propertyType)
            try:
                value = internalPythonType(prop["defaultValue"])
            except ValueError as e:
                raise ValueError(f"Invalid default value for property '{prop['key']}' - expected {internalPythonType} but got {type(prop['defaultValue'])}") from e

            self.add(
                Property(
                    name=SettingString(prop["key"]),
                    type=getPropertyTypeFromString(prop["valueType"]),
                    value=value)
            )

    def _parsePropertiesFromBinaryFile(self, f: io.BufferedIOBase):
        fsize = len(f.read())
        assert fsize >= MIN_FILE_SIZE, "Invalid GARMIN.SET file - File too small"
        f.seek(0)

        [magicValStartOfFile] = struct.unpack('>I', f.read(MAGIC_VALUES_BYTE_SIZE))
        assert magicValStartOfFile == START_OF_FILE_MAGIC_VALUE, f"Invalid GARMIN.SET start of file - first {MAGIC_VALUES_BYTE_SIZE} bytes are 0x{magicValStartOfFile:x} instead of 0x{START_OF_FILE_MAGIC_VALUE:x}"

        self._string_table: SettingStringTable = SettingStringTable(f, advanceSeek=True)

        [midOfFile] = struct.unpack('>I', f.read(MAGIC_VALUES_BYTE_SIZE))
        assert midOfFile == MID_OF_FILE_MAGIC_VALUE, f"Invalid GARMIN.SET mid of file - Read 0x{midOfFile:x} instead of expected 0x{MID_OF_FILE_MAGIC_VALUE:x}"

        # First 4 bytes right after the mid magic value are the length of the remaining property values
        [propertyValuesByteLength] = struct.unpack('>I', f.read(4))
        assert fsize == f.tell() + propertyValuesByteLength, f"Invalid GARMIN.SET file - expected {fsize} but it seems like we'll need to read {f.tell() + propertyValuesByteLength:x} bytes in total"

        [fixedExpectedValue] = struct.unpack('>B', f.read(1))
        assert FIXED_VALUE_AFTER_MID_OF_FILE == fixedExpectedValue, f"Expected fixed value 0x{FIXED_VALUE_AFTER_MID_OF_FILE:x} but got 0x{fixedExpectedValue:x}"

        properties: List[Property] = []
        [numberOfProperties] = struct.unpack('>I', f.read(4))
        for _ in range(numberOfProperties):
            # Append the properties in a temporary list
            properties.append(parsePropertyFromBinary(f, self._string_table))
        assert fsize == f.tell(), f"Invalid GARMIN.SET file - expected {fsize} but it seems like we're done reading the file at {f.tell()} byte"

        # Use the temporary list to initialize the properties and build a new, clean string table
        self.__init__(properties)

    def __init__(self,
                 input: Optional[Union[List[Property], io.BufferedIOBase]] = None):
        self._string_table: SettingStringTable = SettingStringTable()
        self._properties: List[Property] = []
        if input is None:
            return

        if isinstance(input, io.BufferedIOBase):
            assert len(input.read()) >= MIN_FILE_SIZE, "Invalid Garmin settings file - File too small"
            input.seek(0)
            [magicValStartOfFile] = struct.unpack('>I', input.read(MAGIC_VALUES_BYTE_SIZE))
            input.seek(0)
            if magicValStartOfFile == START_OF_FILE_MAGIC_VALUE:
                self._parsePropertiesFromBinaryFile(input)
            else:
                self._parsePropertiesFromJsonFile(input)
            return

        assert isinstance(input, list), f"Invalid input type - expected List[Property] or io.BufferedIOBase - got {type(input)}"
        for prop in input:
            assert isinstance(prop, Property), "Invalid input type - expected List[Property] or io.BufferedIOBase"
            self.add(prop)

    def __getitem__(self, key: Union[SettingString, str]) -> Property:
        return self.get(key)

    def __delitem__(self, key: Union[SettingString, str]):
        self.remove(key)

    def __setitem__(self, key: Union[SettingString, str], propertyValue: Union[SettingString, int, bool, float, str]):
        _, _, internalPythonType = getPropertyTypeStructPack(self.get(key).type)
        if type(propertyValue) == str:
            try:
                modifiedPropertyValue = internalPythonType(propertyValue)
                if (propertyValue == str(modifiedPropertyValue)):
                    propertyValue = modifiedPropertyValue
            except ValueError:
                pass

        assert isinstance(propertyValue, (SettingString, int, bool, float)), \
            (f"Invalid property value type for property '{key}' - expected to be a {internalPythonType} value, "
             f"or a string that is parsable as {internalPythonType}. Got '{propertyValue}'", "Seems like you're"
             " trying to parse a float. Please pass float values with at least one decimal - if not, the value "
             "is interpreted as integer" if internalPythonType is float else "")

        self.edit(key, propertyValue)

    def __contains__(self, key: Union[SettingString, str]) -> bool:
        return self.has_key(key)

    def __len__(self) -> int:
        return len(self._properties)

    def __iter__(self) -> Iterator[Property]:
        return iter(self._properties)

    def has_key(self, key: Union[SettingString, str]) -> bool:
        if type(key) == str:
            key = SettingString(key)

        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def get(self, key: Union[SettingString, str]) -> Property:
        if type(key) is str:
            key = SettingString(key)

        for prop in self._properties:
            if prop.name == key:
                return prop
        raise KeyError(f"Property '{key}' not found")

    def getProperties(self) -> List[Property]:
        return self._properties

    def getStringTable(self) -> SettingStringTable:
        return self._string_table

    def _refreshStringTable(self):
        """
        Remove strings from the string table that are not used
        Call this method after editing or adding a property
        """
        allActiveStrings: Set[SettingString] = set()
        for prop in self._properties:
            allActiveStrings.add(prop.name)
            if prop.type == PropertyType.STRING:
                allActiveStrings.add(cast(SettingString, prop.value))

        for string in self._string_table._string_to_index.keys():
            if string not in allActiveStrings:
                self._string_table.remove(string)

    def edit(self, propertyID: Union[SettingString, str], propertyValue: Union[SettingString, int, bool, float]):
        if type(propertyID) is str:
            propertyID = SettingString(propertyID)

        if propertyID not in self:
            raise KeyError(f"Property with ID '{propertyID}' does not exist")

        for prop in self._properties:
            if prop.name == propertyID:
                _, _, typ = getPropertyTypeStructPack(prop.type)
                if type(propertyValue) != typ:
                    raise ValueError(f"Invalid property value type for property '{propertyID}' - expected {typ} but got {type(propertyValue)}")
                prop.value = propertyValue
                if prop.type == PropertyType.STRING:
                    self._string_table.add(cast(SettingString, propertyValue))
                    self._refreshStringTable()
                break

    def add(self, property: Property):
        if property.name in self:
            raise KeyError(f"A property with the same ID '{property.name}' already exists")

        self._properties.append(property)
        self._string_table.add(property.name)
        if property.type == PropertyType.STRING:
            self._string_table.add(cast(SettingString, property.value))

    def remove(self, propertyID: Union[SettingString, str]):
        if type(propertyID) is str:
            propertyID = SettingString(propertyID)

        if propertyID not in self:
            raise KeyError(f"Property with ID '{propertyID}' does not exist")

        for prop in self._properties:
            if prop.name == propertyID:
                self._properties.remove(prop)
                self._refreshStringTable()
                break

    def _bytesOnlyProperties(self) -> bytes:
        retBytes = struct.pack('>B', FIXED_VALUE_AFTER_MID_OF_FILE) + struct.pack('>i', len(self._properties))
        for prop in self._properties:
            retBytes += prop.bytes(self._string_table)
        return retBytes

    @property
    def bytes(self) -> bytes:
        ret = (struct.pack('>I', START_OF_FILE_MAGIC_VALUE) +
               self._string_table.bytes +
               struct.pack('>I', MID_OF_FILE_MAGIC_VALUE) +
               struct.pack('>I', len(self._bytesOnlyProperties())) +
               self._bytesOnlyProperties())

        return ret

    @property
    def size(self) -> int:
        return len(self.bytes)
