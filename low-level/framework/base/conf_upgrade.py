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
import shutil

from cortx.utils.conf_store import Conf
from cortx.utils.conf_store.error import ConfError
from cortx.utils.kv_store.kv_payload import KvPayload


EXISTING_CONF = "EXISTING_CONF"
NEW_CONF = "NEW_CONF"
MERGED_CONF = "MERGED_CONF"
CHANGED = "CHANGED"
OBSOLETE = "OBSOLETE"


class ConfUpgrade:
    """Performs configuration upgrade when software upgrades."""

    def __init__(self, existing_conf_url, new_conf_url, merged_conf_url):
        """
        Init ConfUpgrade and load config files.

        existing_conf_url: conf store url for existing config file
        new_conf_url: conf store url for new config file
        merged_conf_url: conf store url for merged config file
        """
        self.merged_path = merged_conf_url.split(":/")[1]
        self.merged_path_dir = "/".join(self.merged_path.split("/")[:-1])
        self.existing_path = existing_conf_url.split(":/")[1]
        Conf.load(EXISTING_CONF, existing_conf_url)
        Conf.load(NEW_CONF, new_conf_url)
        os.makedirs(self.merged_path_dir, exist_ok=True)
        with open(self.merged_path, "w"):
            pass
        Conf.load(MERGED_CONF, merged_conf_url)

    def get_changed_keys(self):
        """Get flattened dict of {old_key:key_key}."""
        changed_keys = {}
        if Conf.get(NEW_CONF, CHANGED):
            for changed_key in Conf.get(NEW_CONF, CHANGED):
                changed_key_payload = KvPayload(changed_key)
                key = changed_key_payload.get_keys()[0]
                changed_keys[key] = changed_key_payload.get(key)
        return changed_keys

    def create_merged_config(self):
        """Create merged config file using existing and new configs."""
        existing_keys = set(Conf.get_keys(EXISTING_CONF, key_index=False))
        new_keys = set(Conf.get_keys(NEW_CONF, key_index=False))
        changed_keys = self.get_changed_keys()
        removed_keys = existing_keys - new_keys
        added_keys = new_keys - existing_keys
        retained_keys = existing_keys - removed_keys
        # For newly added keys, get key and value both from new config file
        for key in added_keys:
            Conf.set(MERGED_CONF, key, Conf.get(NEW_CONF, key))
        # For changed keys, get key from new config file and value from old
        # config file
        for old_key, new_key in changed_keys.items():
            Conf.set(MERGED_CONF, new_key, Conf.get(EXISTING_CONF, old_key))
        # For retained keys. get key and value both from existing config file
        for key in retained_keys:
            Conf.set(MERGED_CONF, key, Conf.get(EXISTING_CONF, key))
        # OBSOLETE and CHANGED should always come from new config
        Conf.set(MERGED_CONF, CHANGED, Conf.get(NEW_CONF, CHANGED))
        Conf.set(MERGED_CONF, OBSOLETE, Conf.get(NEW_CONF, OBSOLETE))
        Conf.save(MERGED_CONF)

    def upgrade_existing_config(self):
        """Copy merged config file to existing config file."""
        shutil.copyfile(self.merged_path, self.existing_path)

    def remove_merged_config(self):
        """Remove tmp files created for merging config."""
        os.remove(self.merged_path)
        os.removedirs(self.merged_path_dir)


if __name__ == "__main__":
    new_conf_url = 'yaml:///opt/seagate/cortx/sspl/conf/sspl.conf.LR2.yaml'
    existing_conf_url = 'yaml:///etc/sspl.conf'
    merged_conf_url = 'yaml:///opt/seagate/cortx/sspl/tmp/merged.conf'
    # Only proceed if both existing and new config path are present
    for filepath in [existing_conf_url, new_conf_url]:
        if not os.path.exists(filepath.split(":/")[1]):
            print("Exiting, File %s does not exists" % filepath)
            sys.exit(0)
    conf_upgrade = ConfUpgrade(existing_conf_url, new_conf_url,
                               merged_conf_url)
    try:
        conf_upgrade.create_merged_config()
    except ConfError as e:
        print("Error: %s while upgrading config file, existing config"
              "file is retained" % e)
    else:
        conf_upgrade.upgrade_existing_config()
    finally:
        conf_upgrade.remove_merged_config()
