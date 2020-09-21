# -*- mode: python ; coding: utf-8 -*-
#!/usr/bin/env python3

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

import sys
import os
import re
import PyInstaller.utils.hooks

spec_root = os.path.abspath(SPECPATH)

def import_list(sspl_path, walk_path):
    import_list = []
    keywords = ["json_msgs", "sensors", "framework", "actuators"]
    for root, directories, filenames in os.walk(walk_path):
        for filename in filenames:
            if re.match(r'.*.\.py$', filename) and filename != '__init__.py':
                file = os.path.join(root, filename).rsplit('.', 1)[0]\
                    .replace(sspl_path + "/low-level/", "").replace("/", ".")
                for key in keywords:
                    if key in file:
                        import_list.append(file)
    return import_list

product = '<PRODUCT>'
sspl_path = '<SSPL_PATH>'
product_module_list = import_list(sspl_path, sspl_path)
#product_module_list+=['pysnmp.smi.exval','pysnmp.cache'] + PyInstaller.utils.hooks.collect_submodules('pysnmp.smi.mibs') + PyInstaller.utils.hooks.collect_submodules('pysnmp.smi.mibs.instances')

block_cipher = None

# test code for pysnmp.smi.mib ##############################
import PyInstaller.utils.hooks
hiddenimports = ['pysnmp.smi.exval','pysnmp.cache'] + PyInstaller.utils.hooks.collect_submodules('pysnmp.smi.mibs') + PyInstaller.utils.hooks.collect_submodules('pysnmp.smi.mibs.instances')
pysnmp_smi = Analysis([sspl_path + '/low-level/sensors/impl/generic/SNMP_traps2.py'],
            pathex=[spec_root + '/sspl', spec_root + '/sspl/low-level', spec_root + '/sspl/low-level/framework', spec_root + '/sspl/low-level/message_handlers'],
            hiddenimports=hiddenimports,
            hookspath=None,
            runtime_hooks=None)
x = Tree('/root/.local/lib/python3.6/site-packages/pysnmp/smi/mibs',prefix='pysnmp/smi/mibs',excludes='.py')
pysnmp_smi_pyz = PYZ(pysnmp_smi.pure)
pysnmp_smi_exe = EXE(pysnmp_smi_pyz,
         pysnmp_smi.scripts,
         pysnmp_smi.binaries,
         pysnmp_smi.zipfiles,
         pysnmp_smi.datas,
         x,
         name='testSNMP',
         debug=False,
         strip=None,
         upx=True,
         console=True )
####################################################

sspl_ll_d = Analysis([sspl_path + '/low-level/framework/sspl_ll_d'],
             pathex=[spec_root + '/sspl', spec_root + '/sspl/low-level', spec_root + '/sspl/low-level/framework', spec_root + '/sspl/low-level/message_handlers'],
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

resource_health_view  = Analysis([sspl_path + '/low-level/files/opt/seagate/sspl/bin/generate_resource_health_view/resource_health_view'],
             pathex=[spec_root + '/sspl', spec_root + '/sspl/low-level', spec_root + '/sspl/low-level/framework', spec_root + '/sspl/low-level/message_handlers'],
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

sspl_bundle_generate  = Analysis([sspl_path + '/low-level/files/opt/seagate/sspl/bin/generate_sspl_bundle/sspl_bundle_generate'],
             pathex=[spec_root + '/sspl', spec_root + '/sspl/low-level', spec_root + '/sspl/low-level/framework', spec_root + '/sspl/low-level/message_handlers'],
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
MERGE( (sspl_ll_d, 'sspl_ll_d', 'sspl_ll_d'),
       (resource_health_view, 'resource_health_view', 'resource_health_view'),
       (sspl_bundle_generate, 'sspl_bundle_generate', 'sspl_bundle_generate') )

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

#sspl_bundle_generate
sspl_bundle_generate_pyz = PYZ(sspl_bundle_generate.pure, sspl_bundle_generate.zipped_data,
             cipher=block_cipher)

sspl_bundle_generate_exe = EXE(sspl_bundle_generate_pyz,
          sspl_bundle_generate.scripts,
          [],
          exclude_binaries=True,
          name='sspl_bundle_generate',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(
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

               #sspl_bundle_generate
               sspl_bundle_generate_exe,
               sspl_bundle_generate.binaries,
               sspl_bundle_generate.zipfiles,
               sspl_bundle_generate.datas,

               #sspl_tests_exe,
               #sspl_tests.binaries,
               #sspl_tests.zipfiles,
               #sspl_tests.datas,

               ## pysnmp_smi
               pysnmp_smi_exe,
               pysnmp_smi.binaries,
               pysnmp_smi.zipfiles,
               pysnmp_smi.datas,

               strip=False,
               upx=True,
               upx_exclude=[],
               name='lib')
