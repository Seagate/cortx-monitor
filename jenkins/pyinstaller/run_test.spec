# -*- mode: python ; coding: utf-8 -*-
#!/usr/bin/env python3
import sys
import os
import re

spec_root = os.path.abspath(SPECPATH)

def import_list(sspl_path, walk_path):
    import_list = []
    for root, directories, filenames in os.walk(walk_path):
        for filename in filenames:
            if re.match(r'.*.\.py$', filename) and filename != '__init__.py':
                file = os.path.join(root, filename).rsplit('.', 1)[0]\
                    .replace(sspl_path + "/", "").replace("/", ".")
                import_list.append('sspl_test.' + file)
    return import_list

product = '<PRODUCT>'
sspl_path = '<SSPL_PATH>'
sspl_test_path = '<SSPL_TEST_PATH>'

test_module_list = import_list(sspl_test_path, sspl_test_path)
test_module_list.remove('sspl_test.run_test')

block_cipher = None

sspl_tests = Analysis([sspl_test_path + '/run_test.py'],
             pathex=[sspl_test_path, spec_root + '/sspl_test', spec_root + '/sspl_test/framework', spec_root + '/sspl_test/rabbitmq'],
             binaries=[],
             datas=[(sspl_path + '/low-level/json_msgs/schemas/actuators/*.json', '.'),
                    (sspl_path + '/low-level/json_msgs/schemas/sensors/*.json', '.'),
                    (sspl_path + '/low-level/tests/manual/actuator_msgs/*.json', '.'),
                    (sspl_path + '/low-level/tests/manual/actuator_msgs/*.conf', '.')],
             hiddenimports=test_module_list,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

sspl_tests_pyz = PYZ(sspl_tests.pure, sspl_tests.zipped_data,
             cipher=block_cipher)

sspl_tests_exe = EXE(sspl_tests_pyz,
          sspl_tests.scripts,
          [],
          exclude_binaries=True,
          name='sspl_tests',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(sspl_tests_exe,
               sspl_tests.binaries,
               sspl_tests.zipfiles,
               sspl_tests.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='lib')
