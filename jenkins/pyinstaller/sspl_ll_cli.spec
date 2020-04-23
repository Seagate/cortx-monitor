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
                import_list.append('cli.' + file)
    return import_list

product = '<PRODUCT>'
sspl_path = '<SSPL_PATH>'
sspl_cli_path = '<SSPL_CLI_PATH>'
product_path = '<SSPL_PATH>' + '/' + product
product_module_list = import_list(sspl_path, product_path)

block_cipher = None

sspl_ll_cli = Analysis([sspl_cli_path + '/sspl-ll-cli'],
             pathex=[spec_root + '/sspl', spec_root + '/sspl/low-level', spec_root + '/sspl/low-level/framework'],
             binaries=[],
             datas=[(sspl_path + '/low-level/json_msgs/schemas/actuators/*.json', '.'),
                    (sspl_path + '/low-level/json_msgs/schemas/sensors/*.json', '.'),
                    (sspl_path + '/low-level/tests/manual/actuator_msgs/*.json', '.'),
                    (sspl_path + '/low-level/tests/manual/actuator_msgs/*.conf', '.')],
             hiddenimports=product_module_list,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

MERGE( (sspl_ll_cli, 'sspl_ll_cli', 'sspl_ll_cli') )

sspl_ll_cli_pyz = PYZ(sspl_ll_cli.pure, sspl_ll_cli.zipped_data,
            cipher=block_cipher)

sspl_ll_cli_exe = EXE(sspl_ll_cli_pyz,
          sspl_ll_cli.scripts,
          [],
          exclude_binaries=True,
          name='sspl_ll_cli',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(
               sspl_ll_cli_exe,
               sspl_ll_cli.binaries,
               sspl_ll_cli.zipfiles,
               sspl_ll_cli.datas,

               strip=False,
               upx=True,
               upx_exclude=[],
               name='lib')
