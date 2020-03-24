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
                import_list.append('sspl.' + file)
    return import_list

product = '<PRODUCT>'
sspl_path = '<SSPL_PATH>'
product_path = '<SSPL_PATH>' + '/' + product
product_module_list = import_list(sspl_path, product_path)

block_cipher = None

sspl_ll_cli = Analysis([sspl_path + '/low-level/cli/sspl-ll-cli'],
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

sspl_ll_d = Analysis([sspl_path + '/low-level/framework/sspl_ll_d'],
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

resource_health_view  = Analysis([sspl_path + '/low-level/files/opt/seagate/sspl/bin/genrate_resource_health_view/resource_health_view'],
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

#merge
MERGE( (sspl_ll_cli, 'sspl_ll_cli', 'sspl_ll_cli'),
       (sspl_ll_d, 'sspl_ll_d', 'sspl_ll_d'),
       (resource_health_view, 'resource_health_view', 'resource_health_view') )


#sspl_ll_cli
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


#sspl_ll_d
sspl_ll_d_pyz = PYZ(sspl_ll_d.pure, sspl_ll_d.zipped_data,
             cipher=block_cipher)

sspl_ll_d_exe = EXE(sspl_ll_d_pyz,
          sspl_ll_d.scripts,
          [],
          exclude_binaries=True,
          name='sspl_ll_d',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

#resource_health_view
resource_health_view_pyz = PYZ(resource_health_view.pure, resource_health_view.zipped_data,
             cipher=block_cipher)

resource_health_view_exe = EXE(resource_health_view_pyz,
          resource_health_view.scripts,
          [],
          exclude_binaries=True,
          name='resource_health_view',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(
               #sspl_ll_cli
               sspl_ll_cli_exe,
               sspl_ll_cli.binaries,
               sspl_ll_cli.zipfiles,
               sspl_ll_cli.datas,

               #sspl_ll_d
               sspl_ll_d_exe,
               sspl_ll_d.binaries,
               sspl_ll_d.zipfiles,
               sspl_ll_d.datas,

               #resource_health_view
               resource_health_view_exe,
               resource_health_view.binaries,
               resource_health_view.zipfiles,
               resource_health_view.datas,

               #sspl_tests_exe,
               #sspl_tests.binaries,
               #sspl_tests.zipfiles,
               #sspl_tests.datas,

               strip=False,
               upx=True,
               upx_exclude=[],
               name='lib')
