import unittest
import os
import pickle
import consul
import json
import shutil
import sys

sys.path.append('../low-level/files/opt/seagate/sspl/bin/')

from consuldump import ConsulDump

class TestConsulDump(unittest.TestCase):

    def setUp(self):
        self.c = consul.Consul()
        self.c.kv.put("test/dump/foo", pickle.dumps({"key": "value"}))
        self.c.kv.put("test/dump/bar", pickle.dumps(["list"]))
        self.c.kv.put("test_another_key", "another_value")
        self.c.kv.put("test_yet_another_key", pickle.dumps(set([1,2,3,4])))
        self.c.kv.put("test/config/first", "first value")
        self.c.kv.put("test/config/second", "second")

    def test_consuldump_mkdir_creat_a_dir(self):
        consul_dump = ConsulDump()
        consul_dump.mkdir(consul_dump.get_dir())
        self.assertTrue(os.path.exists(f"{consul_dump.location}/consuldump_{consul_dump.time}"))
        os.removedirs(f"{consul_dump.location}/consuldump_{consul_dump.time}")

    def test_consuldump_mkdir_creat_a_dir_at_diffrent_localtion(self):
        consul_dump = ConsulDump(localtion="/home/730724/")
        consul_dump.mkdir(consul_dump.get_dir())
        self.assertTrue(os.path.exists(f"{consul_dump.location}/consuldump_{consul_dump.time}"))
        os.removedirs(f"{consul_dump.location}/consuldump_{consul_dump.time}")

    def test_consuldump_mkdir_creat_a_dir_with_dir_prefix_if_dir_prefix_is_given(self):
        consul_dump = ConsulDump(dir_prefix="foo")
        consul_dump.mkdir(consul_dump.get_dir())
        self.assertTrue(os.path.exists(f"{consul_dump.location}/consuldump_{consul_dump.dir_prefix}_{consul_dump.time}"))
        os.removedirs(f"{consul_dump.location}/consuldump_{consul_dump.dir_prefix}_{consul_dump.time}")

    def test_consuldump_mkdir_should_not_create_a_dir_with_dir_prefix_if_dir_prefix_is_forward_slash(self):
        consul_dump = ConsulDump(dir_prefix="/prefix_with_slash")
        self.assertRaises(TypeError, consul_dump.mkdir)
        self.assertFalse(os.path.exists(f"{consul_dump.location}/consuldump_{consul_dump.dir_prefix}_{consul_dump.time}"))

    def test_consuldump_mkdir_should_not_create_a_new_dir_if_existing_option_is_passed(self):
        consul_dump = ConsulDump(existing=True)

        self.assertEqual(consul_dump.location, consul_dump.get_dir())

    def test_get_values(self):
        consul_dump = ConsulDump(keys={"test/dump":{"hierarchy": False, "dir": ""},
                                      "test_another_key":{"hierarchy": False, "dir": ""}, 
                                      "test_yet_another_key": {"hierarchy": False, "dir": ""}})
        self.assertEqual(consul_dump.get_values("test/dump/foo")[0]['Value'], pickle.dumps({"key": "value"}))

    def test_get_pretty_file_content(self):
        consul_dump = ConsulDump()
        self.assertEqual('{\n    "key": "value"\n}',consul_dump.get_pretty_file_content(pickle.dumps({"key": "value"})))
        self.assertEqual('[\n    "list"\n]',consul_dump.get_pretty_file_content(pickle.dumps(["list"])))
        self.assertEqual('another_value',consul_dump.get_pretty_file_content(b'another_value'))
        self.assertEqual('{1, 2, 3, 4}',consul_dump.get_pretty_file_content(pickle.dumps(set([1,2,3,4]))))

    def test_files_should_be_created_with_directory_hierarchy(self):
        consul_dump = ConsulDump(keys={"test/":{"hierarchy": True, "dir": "cache/data/encl/"}})
        consul_dump.dump()
        expected_files = ["cache/data/encl/test/dump/foo", "cache/data/encl/test/dump/bar",
                         "cache/data/encl/test/config/first", "cache/data/encl/test/config/second",
                        ]
        for expected_file in expected_files:
            print(f"{consul_dump.location}/consuldump_{consul_dump.time}/{expected_file}")
            self.assertTrue(os.path.exists(f"{consul_dump.location}/consuldump_{consul_dump.time}/{expected_file}"))
        shutil.rmtree(f"{consul_dump.location}/consuldump_{consul_dump.time}")
    
    def test_files_should_not_be_created_with_directory_hierarchy(self):
        consul_dump = ConsulDump(keys={"test/":{"hierarchy": False, "dir": "dump_file"}})
        exprected_content = """test/config/first:\nfirst value
test/config/second:\nsecond
test/dump/bar:\n[\n    "list"\n]
test/dump/foo:\n{\n    "key": "value"\n}\n"""
        consul_dump.dump()
        with open(f"{consul_dump.location}/consuldump_{consul_dump.time}/dump_file") as outfile:
            self.assertEqual(exprected_content, outfile.read())

    def tearDown(self):
        self.c.kv.delete("test/dump/foo")
        self.c.kv.delete("test/dump/bar")
        self.c.kv.delete("test_another_key")
        self.c.kv.delete("test_yet_another_key")
        for directory in os.listdir():
            if directory.startswith("consuldump_"):
                shutil.rmtree(directory)



if __name__ == "__main__":
    unittest.main()
