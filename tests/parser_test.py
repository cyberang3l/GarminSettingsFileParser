import hashlib
import io
import os
import shutil
import tempfile
import unittest
from parser import (
    GarminProperties,
    Property,
    PropertyType,
    SettingString,
    SettingStringTable
)
from typing import List, NamedTuple
from unittest.mock import mock_open

testBinary = (b'\xab\xcd\xab\xcd\x00\x00\x00\x55\x00\x05\x4e\x75\x6d\x32\x00\x00'
              b'\x05\x55\x72\x6c\x31\x00\x00\x15\x68\x74\x74\x70\x73\x3a\x2f\x2f'
              b'\x79\x6f\x75\x72\x2e\x75\x72\x6c\x2e\x63\x6f\x6d\x00\x00\x05\x53'
              b'\x74\x72\x32\x00\x00\x14\x61\x6e\x6f\x74\x68\x65\x72\x20\x73\x74'
              b'\x72\x69\x6e\x67\x20\x68\x65\x72\x65\x00\x00\x0a\x55\x73\x65\x4d'
              b'\x69\x6c\x46\x6d\x74\x00\x00\x05\x4e\x75\x6d\x31\x00\xda\x7a\xda'
              b'\x7a\x00\x00\x00\x34\x0b\x00\x00\x00\x05\x03\x00\x00\x00\x00\x01'
              b'\x56\x78\x9a\xbc\x03\x00\x00\x00\x07\x03\x00\x00\x00\x0e\x03\x00'
              b'\x00\x00\x25\x03\x00\x00\x00\x2c\x03\x00\x00\x00\x42\x09\x01\x03'
              b'\x00\x00\x00\x4e\x01\x23\x45\x67\x89')


class TestGarminSettingsClasses(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory before each test
        self.testDir = tempfile.mkdtemp()
        self.testSetOutput = os.path.join(self.testDir, "TESTAPP.SET.tmp")

    def tearDown(self) -> None:
        shutil.rmtree(self.testDir)

    def test_setting_string(self):
        class TestTuple(NamedTuple):
            string: str
            expect_string: str
            expect: SettingString
            expect_strlen: int
            expect_size: int
            expect_bytes: bytes

        testSet = [
            TestTuple(
                string="test_string",
                expect_string="test_string",
                expect=SettingString("test_string"),
                expect_strlen=12,
                expect_size=14,
                expect_bytes=b'\x00\x0ctest_string\x00',
            ),
            TestTuple(
                string="try with some spaces",
                expect_string="try with some spaces",
                expect=SettingString("try with some spaces"),
                expect_strlen=21,
                expect_size=23,
                expect_bytes=b'\x00\x15try with some spaces\x00',
            ),
            TestTuple(
                # Ensure we get rid of the extra null terminators on the input string
                string="try with some spaces\x00\x00",
                expect_string="try with some spaces",
                expect=SettingString("try with some spaces"),
                expect_strlen=21,
                expect_size=23,
                expect_bytes=b'\x00\x15try with some spaces\x00',
            ),
            TestTuple(
                string="",
                expect_string="",
                expect=SettingString(""),
                expect_strlen=1,
                expect_size=3,
                expect_bytes=b'\x00\x01\x00',
            )
        ]

        for test in testSet:
            ss = SettingString(test.string)
            self.assertEqual(test.expect_string, str(ss))
            self.assertEqual(test.expect, ss)
            self.assertEqual(test.expect_strlen, ss.strlen)
            self.assertEqual(test.expect_strlen, len(ss))
            self.assertEqual(test.expect_size, ss.size)
            self.assertEqual(test.expect_size, len(ss.bytes))
            self.assertEqual(test.expect_bytes, ss.bytes)

    def test_setting_string_binary_parse(self):
        class TestTuple(NamedTuple):
            bytes: bytes
            expect: SettingString
            expect_strlen: int
            expect_size: int
            expect_string: str

        testSet = [
            TestTuple(
                bytes=b'\00\x0ctest_string\x00',
                expect=SettingString("test_string"),
                expect_strlen=12,
                expect_size=14,
                expect_string="test_string",
            ),
            TestTuple(
                bytes=b'\00\x15try with some spaces\x00',
                expect=SettingString("try with some spaces"),
                expect_strlen=21,
                expect_size=23,
                expect_string="try with some spaces",
            )
        ]

        for testCase in testSet:
            mocked_file = mock_open(
                read_data=testCase.bytes).return_value
            mocked_file.__class__ = io.BufferedRandom
            ss = SettingString(mocked_file)
            self.assertEqual(testCase.expect, ss)
            self.assertEqual(testCase.expect_string, ss.string)
            self.assertEqual(testCase.expect_strlen, len(ss))
            self.assertEqual(testCase.expect_strlen, ss.strlen)
            self.assertEqual(testCase.expect_size, len(ss.bytes))
            self.assertEqual(testCase.expect_size, ss.size)

    def test_setting_string_only_accepts_valid_ascii(self):
        with self.assertRaises(UnicodeEncodeError):
            SettingString("test string2\u2603")

    def test_setting_string_hash(self):
        self.assertEqual(hash(SettingString("test_string")), hash(SettingString("test_string")))
        self.assertNotEqual(hash(SettingString("test_string")), hash("test_string"))
        self.assertNotEqual(hash(SettingString("other string")), hash("other string"))

    def test_setting_string_as_dict_key(self):
        d = {
            SettingString("test_string"): 1,
            SettingString("test_string2"): "A",
            SettingString("test_string3"): 3
        }
        self.assertEqual(d.get(SettingString("test_string")), 1)
        self.assertEqual(d.get(SettingString("test_string2")), "A")
        self.assertEqual(d.get(SettingString("test_string3")), 3)

    def test_setting_string_table(self):
        table = SettingStringTable([
            SettingString("str"),
            SettingString("str1"),
            SettingString("str2"),
            SettingString("string3")
        ])

        self.assertEqual(table[SettingString("str")], 0)
        self.assertEqual(table[0], SettingString("str"))
        self.assertEqual(table[SettingString("str1")], 6)
        self.assertEqual(table[6], SettingString("str1"))
        self.assertEqual(table[SettingString("str2")], 13)
        self.assertEqual(table[13], SettingString("str2"))
        self.assertEqual(table[SettingString("string3")], 20)
        self.assertEqual(table[20], SettingString("string3"))

        self.assertTrue(SettingString("str1") in table)
        self.assertTrue(table.has_key(SettingString("str1")))
        self.assertTrue(table.has_key(0))
        self.assertTrue(table.has_key(13))
        self.assertFalse(SettingString("strstr") in table)
        self.assertFalse(table.has_key(SettingString("strstr")))
        self.assertFalse(table.has_key(1))

        expectBytes = b'\x00\x04str\x00\x00\x05str1\x00\x00\x05str2\x00\x00\x08string3\x00'
        self.assertEqual(len(table), 4)
        self.assertEqual(table.size, 30)
        self.assertEqual(table._bytesOnlyStringTable(), expectBytes)
        self.assertEqual(table.bytes, b'\x00\x00\00\x1E' + expectBytes)

        # Add existing string should not change anything
        table.add(SettingString("str1"))
        expectBytes = b'\x00\x04str\x00\x00\x05str1\x00\x00\x05str2\x00\x00\x08string3\x00'
        self.assertEqual(len(table), 4)
        self.assertEqual(table.size, 30)
        self.assertEqual(table._bytesOnlyStringTable(), expectBytes)
        self.assertEqual(table.bytes, b'\x00\x00\00\x1E' + expectBytes)

        # Add a new string
        table.add(SettingString("new"))
        expectBytes = b'\x00\x04str\x00\x00\x05str1\x00\x00\x05str2\x00\x00\x08string3\x00\x00\x04new\x00'
        self.assertEqual(len(table), 5)
        self.assertEqual(table.size, 36)
        self.assertEqual(table._bytesOnlyStringTable(), expectBytes)
        self.assertEqual(table.bytes, b'\x00\x00\00\x24' + expectBytes)

        # Delete a string with the del keyword passing a SettingString as a key
        del table[SettingString("str")]
        expectBytes = b'\x00\x05str1\x00\x00\x05str2\x00\x00\x08string3\x00\x00\x04new\x00'
        self.assertEqual(len(table), 4)
        self.assertEqual(table.size, 30)
        self.assertEqual(table._bytesOnlyStringTable(), expectBytes)
        self.assertEqual(table.bytes, b'\x00\x00\00\x1E' + expectBytes)

        # Delete a string with the del keyword passing an int as a key
        del table[7]
        expectBytes = b'\x00\x05str1\x00\x00\x08string3\x00\x00\x04new\x00'
        self.assertEqual(len(table), 3)
        self.assertEqual(table.size, 23)
        self.assertEqual(table._bytesOnlyStringTable(), expectBytes)
        self.assertEqual(table.bytes, b'\x00\x00\00\x17' + expectBytes)

        # Delete a string with the remove method passing a SettingString as a key
        table.remove(SettingString("new"))
        expectBytes = b'\x00\x05str1\x00\x00\x08string3\x00'
        self.assertEqual(len(table), 2)
        self.assertEqual(table.size, 17)
        self.assertEqual(table._bytesOnlyStringTable(), expectBytes)
        self.assertEqual(table.bytes, b'\x00\x00\00\x11' + expectBytes)

        # Delete a string with the remove method passing an int as a key
        table.remove(0)
        expectBytes = b'\x00\x08string3\x00'
        self.assertEqual(len(table), 1)
        self.assertEqual(table.size, 10)
        self.assertEqual(table._bytesOnlyStringTable(), expectBytes)
        self.assertEqual(table.bytes, b'\x00\x00\00\x0A' + expectBytes)

        emptyTable = SettingStringTable()
        self.assertEqual(len(emptyTable), 0)
        self.assertEqual(emptyTable.size, 0)
        self.assertEqual(emptyTable.bytes, b'\x00\x00\x00\x00')
        self.assertFalse(emptyTable.has_key(0))

    def test_setting_string_table_binary_parse(self):
        inputBytes = b'\x00\x00\x00\x24\x00\x04str\x00\x00\x05str1\x00\x00\x05str2\x00\x00\x08string3\x00\x00\x04new\x00'
        expectTable = SettingStringTable([
            SettingString("str"),
            SettingString("str1"),
            SettingString("str2"),
            SettingString("string3"),
            SettingString("new")
        ])
        with open(self.testSetOutput, "wb") as f:
            f.write(inputBytes)

        with open(self.testSetOutput, "rb") as binary_file:
            table = SettingStringTable(binary_file)
            self.assertEqual(len(table), 5)
            self.assertEqual(table.size, len(inputBytes) - 4)
            self.assertEqual(table.size, 36)
            self.assertEqual(table.size, expectTable.size)
            self.assertCountEqual(table._strings, expectTable._strings)
            self.assertCountEqual(table._index_to_string, expectTable._index_to_string)
            self.assertCountEqual(table._string_to_index, expectTable._string_to_index)

            # Both tables contain the same strings in the same order
            # Should be equal and have the same hash
            self.assertEqual(table, expectTable)
            self.assertEqual(hash(table), hash(expectTable))

            # Both tables contain the same strings, but not in the same order
            # Should be equal BUT NOT have the same hash
            expectTable.remove(SettingString("str1"))
            expectTable.add(SettingString("str1"))
            self.assertEqual(table, expectTable)
            self.assertNotEqual(hash(table), hash(expectTable))

    def test_setting_string_table_binary_parse_invalid(self):
        # Data in file shorter than the table length indicated by the first 4 bytes
        inputBytesInvalid = b'\x00\x00\x00\x24\x00\x04str\x00\x00\x05str1\x00\x00\x05str2\x00\x00\x08string3\x00\x00\x04new'
        with open(self.testSetOutput, "wb") as f:
            f.write(inputBytesInvalid)

        with open(self.testSetOutput, "rb") as binary_file:
            with self.assertRaisesRegex(ValueError, "Expecting at least 36 bytes, got 35"):
                SettingStringTable(binary_file)

    def test_garmin_properties(self):
        input = [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x23456789),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("another string here")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
        ]

        properties = GarminProperties(input)

        self.assertEqual(len(properties), 5)

        # Ensure the properties and string table are correctly instantiated
        self.assertCountEqual(properties.getProperties(), input)
        self.assertCountEqual(properties.getStringTable()._strings, [
            SettingString("Num1"),
            SettingString("Num2"),
            SettingString("Url1"),
            SettingString("Str2"),
            SettingString("UseMilFmt"),
            SettingString("https://your.url.com"),
            SettingString("another string here"),
        ])

        # Ensure we can get the properties by name and the __getitem__ magic method works
        # Plain strings ans SettingString should work
        self.assertEqual(properties["Num1"].name, SettingString("Num1"))
        self.assertEqual(properties.get("Num1").name, SettingString("Num1"))
        self.assertEqual(properties.get(SettingString("Num1")).name, SettingString("Num1"))
        self.assertEqual(properties[SettingString("Num1")].type, PropertyType.INT32)
        self.assertEqual(properties[SettingString("Num1")].value, 0x23456789)
        with self.assertRaisesRegex(KeyError, f"Property 'Num3' not found"):
            properties[SettingString("Num3")]
        with self.assertRaisesRegex(KeyError, f"Property 'Num3' not found"):
            properties["Num3"]

        self.assertTrue(SettingString("Num1") in properties)
        self.assertTrue("Num1" in properties)
        self.assertTrue(properties.has_key("Num1"))
        self.assertFalse("Num5" in properties)
        self.assertFalse(properties.has_key(SettingString("Num5")))

    def test_property(self):
        class TestTuple(NamedTuple):
            property: Property
            string_table: SettingStringTable
            expect_len: int
            expect_bytes: bytes
            expect_fail: str

        testSet = [
            TestTuple(
                property=Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x23456789),
                string_table=SettingStringTable([SettingString("Num1")]),
                expect_len=10,
                expect_bytes=b'\x03\x00\x00\x00\x00\x01\x23\x45\x67\x89',
                expect_fail=""
            ),
            TestTuple(
                property=Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x6789),
                string_table=SettingStringTable([SettingString("RandomString1"), SettingString("Num1")]),
                expect_len=10,
                expect_bytes=b'\x03\x00\x00\x00\x10\x01\x00\x00\x67\x89',
                expect_fail=""
            ),
            TestTuple(
                property=Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x6789),
                string_table=SettingStringTable(),
                expect_len=10,
                expect_bytes=b'\x03\x00\x00\x00\x10\x01\x00\x00\x67\x89',
                expect_fail="Property name 'Num1' not in string table - cannot serialize property"
            ),
            TestTuple(
                property=Property(name=SettingString("String"), type=PropertyType.STRING, value=SettingString("My super secret string")),
                string_table=SettingStringTable([SettingString("String"), SettingString("My super secret string")]),
                expect_len=10,
                expect_bytes=b'\x03\x00\x00\x00\x00\x03\x00\x00\x00\x09',
                expect_fail=""
            ),
            TestTuple(
                property=Property(name=SettingString("String"), type=PropertyType.STRING, value=SettingString("My super secret string")),
                string_table=SettingStringTable([SettingString("String")]),
                expect_len=10,
                expect_bytes=b'\x03\x00\x00\x00\x00\x03\x00\x00\x00\x09',
                expect_fail="String property value 'My super secret string' not in string table - cannot serialize property"
            ),
            TestTuple(
                property=Property(name=SettingString("String"), type=PropertyType.STRING, value=SettingString("My super secret string")),
                string_table=SettingStringTable([SettingString("A"), SettingString("String"), SettingString("Random intermediate string"), SettingString("My super secret string")]),
                expect_len=10,
                expect_bytes=b'\x03\x00\x00\x00\x04\x03\x00\x00\x00\x2A',
                expect_fail=""
            ),
            TestTuple(
                property=Property(name=SettingString("Boolean"), type=PropertyType.BOOLEAN, value=True),
                string_table=SettingStringTable([SettingString("AB"), SettingString("Boolean")]),
                expect_len=7,
                expect_bytes=b'\x03\x00\x00\x00\x05\x09\x01',
                expect_fail=""
            ),
            TestTuple(
                property=Property(name=SettingString("Boolean"), type=PropertyType.BOOLEAN, value=False),
                string_table=SettingStringTable([SettingString("AB"), SettingString("Boolean")]),
                expect_len=7,
                expect_bytes=b'\x03\x00\x00\x00\x05\x09\x00',
                expect_fail=""
            ),
            TestTuple(
                property=Property(name=SettingString("Float"), type=PropertyType.FLOAT32, value=21.3456),
                string_table=SettingStringTable([SettingString("Float")]),
                expect_len=10,
                expect_bytes=b'\x03\x00\x00\x00\x00\x02\x41\xAA\xC3\xCA',
                expect_fail=""
            ),
            TestTuple(
                property=Property(name=SettingString("Double"), type=PropertyType.DOUBLE64, value=121245454521.34568723),
                string_table=SettingStringTable([SettingString("Double")]),
                expect_len=14,
                expect_bytes=b'\x03\x00\x00\x00\x00\x0F\x42\x3C\x3A\xCA\xD0\xB9\x58\x7F',
                expect_fail=""
            ),

        ]

        for test in testSet:
            if test.expect_fail:
                with self.assertRaisesRegex(AssertionError, test.expect_fail):
                    self.assertEqual(test.expect_bytes, test.property.bytes(test.string_table))
            else:
                self.assertEqual(test.expect_bytes, test.property.bytes(test.string_table))
                self.assertEqual(test.expect_len, len(test.property.bytes(test.string_table)))

    def test_garmin_properties_does_not_allow_duplicate_properties(self):
        input = [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x23456789),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("another string here")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x23456789),
        ]
        with self.assertRaisesRegex(KeyError, "A property with the same ID 'Num1' already exists"):
            GarminProperties(input)

    def test_garmin_edit_properties(self):
        input = [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x23456789),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("another string here")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
        ]

        properties = GarminProperties(input)
        # Edit a property should update the value only if the type is correct or
        # raise an error otherwise
        properties.edit("Num1", 0xABCDEF01)
        self.assertEqual(properties["Num1"].value, 0xABCDEF01)
        with self.assertRaisesRegex(ValueError, "Invalid property value type for property 'Num1' - expected <class 'int'> but got <class 'float'>"):
            properties.edit("Num1", 0.23)

        properties["UseMilFmt"] = False
        self.assertEqual(properties["UseMilFmt"].value, False)
        with self.assertRaisesRegex(ValueError, "Invalid property value type for property 'UseMilFmt' - expected <class 'bool'> but got <class 'int'>"):
            properties.edit("UseMilFmt", 123)

        with self.assertRaisesRegex(KeyError, "Property with ID 'Number10' does not exist"):
            properties.edit("Number10", 123)

        # Edit a string property should update the value and the string table
        properties.edit("Str2", SettingString("new value"))
        self.assertEqual(properties["Str2"].value, SettingString("new value"))
        self.assertCountEqual(properties.getStringTable()._strings, [
            SettingString("Num1"),
            SettingString("Num2"),
            SettingString("Url1"),
            SettingString("Str2"),
            SettingString("UseMilFmt"),
            SettingString("https://your.url.com"),
            SettingString("new value"),
        ])
        self.assertCountEqual(properties.getProperties(), [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0xABCDEF01),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("new value")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=False),
        ])

        self.assertEqual(len(properties), 5)

    def test_garmin_add_remove_properties(self):
        input = [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0xABCDEF01),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("another string here")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
        ]

        properties = GarminProperties(input)

        # Do not accept duplite properties
        with self.assertRaisesRegex(KeyError, "A property with the same ID 'Num1' already exists"):
            properties.add(Property(name=SettingString("Num1"), type=PropertyType.FLOAT32, value=1.23))

        # Add a new property should update the string table
        properties.add(Property(name=SettingString("NewProp"), type=PropertyType.STRING, value=SettingString("new property")))
        self.assertEqual(len(properties), 6)
        self.assertCountEqual(properties.getStringTable()._strings, [
            SettingString("Num1"),
            SettingString("Num2"),
            SettingString("Url1"),
            SettingString("Str2"),
            SettingString("UseMilFmt"),
            SettingString("https://your.url.com"),
            SettingString("another string here"),
            SettingString("NewProp"),
            SettingString("new property"),
        ])
        self.assertCountEqual(properties.getProperties(), [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0xABCDEF01),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("another string here")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
            Property(name=SettingString("NewProp"), type=PropertyType.STRING, value=SettingString("new property")),
        ])

        properties.add(Property(name=SettingString("NewProp2"), type=PropertyType.FLOAT32, value=1.23))
        self.assertEqual(len(properties), 7)
        self.assertCountEqual(properties.getStringTable()._strings, [
            SettingString("Num1"),
            SettingString("Num2"),
            SettingString("Url1"),
            SettingString("Str2"),
            SettingString("UseMilFmt"),
            SettingString("https://your.url.com"),
            SettingString("another string here"),
            SettingString("NewProp"),
            SettingString("NewProp2"),
            SettingString("new property"),
        ])
        self.assertCountEqual(properties.getProperties(), [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0xABCDEF01),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("another string here")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
            Property(name=SettingString("NewProp"), type=PropertyType.STRING, value=SettingString("new property")),
            Property(name=SettingString("NewProp2"), type=PropertyType.FLOAT32, value=1.23),
        ])

        # Remove a property should update the string table
        properties.remove("NewProp")
        self.assertEqual(len(properties), 6)
        self.assertCountEqual(properties.getStringTable()._strings, [
            SettingString("Num1"),
            SettingString("Num2"),
            SettingString("Url1"),
            SettingString("Str2"),
            SettingString("UseMilFmt"),
            SettingString("https://your.url.com"),
            SettingString("another string here"),
            SettingString("NewProp2"),
        ])
        self.assertCountEqual(properties.getProperties(), [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0xABCDEF01),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("another string here")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
            Property(name=SettingString("NewProp2"), type=PropertyType.FLOAT32, value=1.23),
        ])

        del properties["NewProp2"]
        self.assertEqual(len(properties), 5)
        self.assertCountEqual(properties.getStringTable()._strings, [
            SettingString("Num1"),
            SettingString("Num2"),
            SettingString("Url1"),
            SettingString("Str2"),
            SettingString("UseMilFmt"),
            SettingString("https://your.url.com"),
            SettingString("another string here"),
        ])
        self.assertCountEqual(properties.getProperties(), [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0xABCDEF01),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("another string here")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
        ])

        del properties[SettingString("Str2")]
        self.assertEqual(len(properties), 4)
        self.assertCountEqual(properties.getStringTable()._strings, [
            SettingString("Num1"),
            SettingString("Num2"),
            SettingString("Url1"),
            SettingString("UseMilFmt"),
            SettingString("https://your.url.com"),
        ])
        self.assertCountEqual(properties.getProperties(), [
            Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0xABCDEF01),
            Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC),
            Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
            Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
        ])

        with self.assertRaisesRegex(KeyError, "Property with ID 'Num3' does not exist"):
            properties.remove(SettingString("Num3"))

        with self.assertRaisesRegex(KeyError, "Property with ID 'Num3' does not exist"):
            del properties["Num3"]

    def test_garmin_properties_to_binary(self):

        class TestSet(NamedTuple):
            props: List[Property]
            expect_only_property_bytes: bytes
            expect_all_bytes: bytes
            expect_size: int

        testSet = [
            TestSet(
                props=[
                    Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x7BCDEF01),
                    Property(name=SettingString("Num2"), type=PropertyType.INT32, value=0x56789ABC)
                ],
                expect_only_property_bytes=b'\x0B\x00\x00\x00\x02\x03\x00\x00\x00\x00\x01\x7B\xCD\xEF\x01\x03\x00\x00\x00\x07\x01\x56\x78\x9A\xBC',
                expect_all_bytes=(b'\xAB\xCD\xAB\xCD' +
                                  SettingStringTable([SettingString("Num1"), SettingString("Num2")]).bytes +
                                  b'\xDA\x7A\xDA\x7A' + b'\x00\x00\x00\x19' + b'\x0B' +
                                  b'\x00\x00\x00\x02\x03\x00\x00\x00\x00\x01\x7B\xCD\xEF\x01\x03\x00\x00\x00\x07\x01\x56\x78\x9A\xBC'),
                expect_size=55,  # 4 + 4 + 7 + 7+ 4 + 4 + 1 + 24
            ),
            TestSet(
                props=[
                    Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x7BCDEF01),
                    Property(name=SettingString("Str1"), type=PropertyType.STRING, value=SettingString("Num1"))
                ],
                expect_only_property_bytes=b'\x0B\x00\x00\x00\x02\x03\x00\x00\x00\x00\x01\x7B\xCD\xEF\x01\x03\x00\x00\x00\x07\x03\x00\x00\x00\x00',
                expect_all_bytes=(b'\xAB\xCD\xAB\xCD' +
                                  SettingStringTable([SettingString("Num1"), SettingString("Str1")]).bytes +
                                  b'\xDA\x7A\xDA\x7A' + b'\x00\x00\x00\x19' + b'\x0B' +
                                  b'\x00\x00\x00\x02\x03\x00\x00\x00\x00\x01\x7B\xCD\xEF\x01\x03\x00\x00\x00\x07\x03\x00\x00\x00\x00'),
                # Duplicate string is only added once - same size like before
                expect_size=55,
            ),
            TestSet(
                props=[
                    Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x7BCDEF01),
                    Property(name=SettingString("Str1"), type=PropertyType.STRING, value=SettingString("StrVal"))
                ],
                expect_only_property_bytes=b'\x0B\x00\x00\x00\x02\x03\x00\x00\x00\x00\x01\x7B\xCD\xEF\x01\x03\x00\x00\x00\x07\x03\x00\x00\x00\x0E',
                expect_all_bytes=(b'\xAB\xCD\xAB\xCD' +
                                  SettingStringTable([SettingString("Num1"), SettingString("Str1"), SettingString("StrVal")]).bytes +
                                  b'\xDA\x7A\xDA\x7A' + b'\x00\x00\x00\x19' + b'\x0B' +
                                  b'\x00\x00\x00\x02\x03\x00\x00\x00\x00\x01\x7B\xCD\xEF\x01\x03\x00\x00\x00\x07\x03\x00\x00\x00\x0E'),
                expect_size=64,  # 4 + 4 + 7 + 7 + 9 + 4 + 4 + 1 + 24
            ),
            TestSet(
                props=[
                    Property(name=SettingString("Num1"), type=PropertyType.INT32, value=0x7BCDEF01),
                    Property(name=SettingString("Str1"), type=PropertyType.STRING, value=SettingString("StrVal")),
                    Property(name=SettingString("Bool"), type=PropertyType.BOOLEAN, value=True),
                ],
                expect_only_property_bytes=b'\x0B\x00\x00\x00\x03\x03\x00\x00\x00\x00\x01\x7B\xCD\xEF\x01\x03\x00\x00\x00\x07\x03\x00\x00\x00\x0E\x03\x00\x00\x00\x17\x09\x01',
                expect_all_bytes=(b'\xAB\xCD\xAB\xCD' +
                                  SettingStringTable([SettingString("Num1"), SettingString("Str1"), SettingString("StrVal"), SettingString("Bool")]).bytes +
                                  b'\xDA\x7A\xDA\x7A' + b'\x00\x00\x00\x20' + b'\x0B' +
                                  b'\x00\x00\x00\x03\x03\x00\x00\x00\x00\x01\x7B\xCD\xEF\x01\x03\x00\x00\x00\x07\x03\x00\x00\x00\x0E\x03\x00\x00\x00\x17\x09\x01'),
                expect_size=78,  # 4 + 4 + 7 + 7 + 9 + 7 + 4 + 4 + 1 + 31
            )
        ]

        for i, test in enumerate(testSet):
            gp = GarminProperties()
            for prop in test.props:
                gp.add(prop)

            self.assertEqual(gp._bytesOnlyProperties(), test.expect_only_property_bytes, f"failed on test {i}")
            self.assertEqual(gp.bytes, test.expect_all_bytes, f"failed on test {i}")
            self.assertEqual(gp.size, test.expect_size, f"failed on test {i}")

            with open(self.testSetOutput, "wb") as f:
                f.write(test.expect_all_bytes)

            with open(self.testSetOutput, "rb") as binary_file:
                gp = GarminProperties(binary_file)
                self.assertCountEqual(gp.getProperties(), test.props, f"failed on test {i}")
                self.assertEqual(gp._bytesOnlyProperties(), test.expect_only_property_bytes, f"failed on test {i}")
                self.assertEqual(gp.bytes, test.expect_all_bytes, f"failed on test {i}")
                self.assertEqual(gp.size, test.expect_size, f"failed on test {i}")

    def test_read_write_garmin_properties_from_binary(self):
        # Write the binary file
        with open(self.testSetOutput, "wb") as f:
            f.write(testBinary)

        # Get the original hash
        orig_digest = ""
        with open(self.testSetOutput, "rb") as f:
            digest = hashlib.file_digest(f, "sha256")
            orig_digest = digest.hexdigest()

        # Read the binary file into a GarminProperties object
        gp = None
        with open(self.testSetOutput, "rb") as binary_file:
            gp = GarminProperties(binary_file)
            self.assertEqual(gp.size, 153)
            self.assertEqual(gp.size, len(testBinary))
            self.assertEqual(len(gp.getProperties()), 5)
            self.assertEqual(len(gp), 5)
            self.assertEqual(gp.bytes, testBinary)

        # Write the GarminProperties object back to a new binary file
        writeFile = f"{self.testSetOutput}.2"
        with open(writeFile, "wb") as f:
            f.write(gp.bytes)

        # Get the hash of the newly written file
        written_digest = ""
        with open(writeFile, "rb") as f:
            digest = hashlib.file_digest(f, "sha256")
            written_digest = digest.hexdigest()

        # Compare the original and written hashes to ensure they are the same
        self.assertEqual(orig_digest, written_digest)

    def test_read_write_garmin_properties_from_json(self):
        # Read from JSON file
        with open("tests/TestApp-settings.json", "rb") as f:
            gp = GarminProperties(f)
            self.assertEqual(len(gp.getProperties()), 5)
            self.assertEqual(len(gp), 5)
            self.assertCountEqual(gp.getProperties(), [
                Property(name=SettingString("UseMilFmt"), type=PropertyType.BOOLEAN, value=True),
                Property(name=SettingString("Url1"), type=PropertyType.STRING, value=SettingString("https://your.url.com")),
                Property(name=SettingString("Str2"), type=PropertyType.STRING, value=SettingString("https://your.proxy.com")),
                Property(name=SettingString("Num1"), type=PropertyType.INT32, value=591751049),
                Property(name=SettingString("Num2"), type=PropertyType.INT32, value=2023406814),
            ])
