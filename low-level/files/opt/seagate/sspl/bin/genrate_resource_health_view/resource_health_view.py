#!/usr/bin/python3.6

import json
import os
import sys
import socket
import time

# Add the top level directories
parentdir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parentdir)
from common.utils.store_factory import store
from common.platforms.realstor.realstor_enclosure import realstor_enclosure
from common.utils.ipmi_client import IpmiFactory

class SSPLHealthView(object):
    """docstring for SSPLHealthView"""

    persistent_data_location = '/var/eos/sspl/data/'
    storage_encl_dir = persistent_data_location+'encl/frus/'

    encl_disks_filename = storage_encl_dir+'disks/'
    encl_psus_filename = storage_encl_dir+'psus/psudata.json'
    encl_controllers_filename = storage_encl_dir+'controllers/controllerdata.json'
    encl_fans_filename = storage_encl_dir+'fanmodules/fanmodule_data.json'
    encl_sideplane_exp_filename = storage_encl_dir+'sideplane_expanders/sideplane_expanders_data.json'
    encl_logical_volumes_filename = storage_encl_dir+'logical_volumes/logicalvolumedata.json'

    encl_disk_resource_type = "enclosure:fru:disk"
    encl_controller_resource_type = "enclosure:fru:controller"
    encl_fan_resource_type = "enclosure:fru:fan"
    encl_psu_resource_type = "enclosure:fru:psu"
    encl_sideplane_resource_type = "enclosure:fru:sideplane"
    encl_logical_volume_resource_type = "enclosure:eos:logical_volume"
    encl_sas_resource_type = "enclosure:interface:sas"

    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "1"
    RACK_ID = "1"
    NODE_ID = socket.getfqdn()
    CLUSTER_ID = "1"
    RESOURCE_HEALTH_VIEW_PATH = '/tmp/sspl/data/resource_health_view.json'
    TEMPLATE_SCHEMA_FILE = parentdir+'/resource_health_view_template.json'

    NODE_REQUEST_MAP = {
        "disk" : "Drive Slot / Bay",
        "fan" : "Fan",
        "psu" : "Power Supply"
    }

    def __init__(self):

        self.sspl_service_status = os.system('systemctl status sspl-ll > /dev/null')
        self.fru_id_map = None
        self.sensor_id_map = None
        self.ipmi_fru_lst = ['disk', 'fan', 'psu']
        self.sensor_list = ['temperature', 'current', 'voltage']
        ipmi_factory = IpmiFactory()
        self._executor = ipmi_factory.get_implementor("ipmitool")
        try:
            self._resource_health_view = json.loads(open(self.TEMPLATE_SCHEMA_FILE).read())

        except Exception as e:
            print("Error in reading resource health view template file: {0}".format(e))
            sys.exit(1)
        self._resource_health_view['cluster']['sites'][self.SITE_ID] =\
            self._resource_health_view['cluster']['sites'].pop('site_id')

        self._resource_health_view['cluster']['sites'][self.SITE_ID]['rack']\
            [self.RACK_ID] = self._resource_health_view['cluster']['sites']\
                [self.SITE_ID]['rack'].pop('rack_id')

        self._resource_health_view['cluster']['sites'][self.SITE_ID]['rack']\
            [self.RACK_ID]['nodes'][self.NODE_ID] = self._resource_health_view['cluster']\
                ['sites'][self.SITE_ID]['rack'][self.RACK_ID]['nodes'].pop('node_id')

        if os.path.exists(self.RESOURCE_HEALTH_VIEW_PATH):
            print("Resource Health view JSON file already exists, overriding ...!")

        if self.sspl_service_status == 0:
            print("SSPL services is already running, ignoring persistent cache creation ..!")

    def build_health_view_storage_encl_cache(self, category):

        try:
            storage_encl_health_json = self._resource_health_view['cluster']['sites']\
                                                [self.SITE_ID]['rack'][self.RACK_ID]\
                                                ['nodes'][self.NODE_ID]['storage_encl']
        except Exception as e:
            print("Error while extracting values from health view json % : " % e)
            return False

        if category == 'hw':
            disk_data = storage_encl_health_json['hw']['fru']['disks']
            disks_info = self.build_encl_disks_cache()
            disk_data.update({"health": "", "disks_info": disks_info})
            self.build_system_persistent_cache()

            psu_data = storage_encl_health_json['hw']['fru']['psus']
            psus_info = self.build_encl_psus_cache()
            psu_data.update({"health": "", "psus_info": psus_info})

            cntrl_data = storage_encl_health_json['hw']['fru']['controllers']
            controllers_info = self.build_encl_controllers_cache()
            cntrl_data.update({"health": "", "controllers_info": controllers_info})

            fan_data = storage_encl_health_json['hw']['fru']['fans']
            fans_info = self.build_encl_fans_cache()
            fan_data.update({"health": "", "fans_info": fans_info})

            spln_data = storage_encl_health_json['hw']['fru']['sideplane_expander']
            sideplane_info = self.build_encl_sideplane_expander_cache()
            spln_data.update({"health": "", "sideplane_info": sideplane_info})

        elif category == 'sw':
            logvol_data = storage_encl_health_json['sw']['logical_volume']
            logicalvolume_info =  self.build_encl_logical_volume_cache()
            logvol_data.update(logicalvolume_info)

        elif category == 'interfaces':
            sas_port_data = storage_encl_health_json['interfaces']['sas_port']
            sas_port_info =  self.build_encl_sas_port_instances()
            sas_port_data.update({"health": "", "sas_port_info": sas_port_info})

        elif category == 'platform_sensors':
            ps_data = self.build_encl_platform_sensors_instances(self.sensor_list)
            for plsn in self.sensor_list:
                sensor_data = storage_encl_health_json['platform_sensors'][plsn]
                sensor_data.update({"health": "", plsn+"_info": ps_data[plsn]})


        try:
            with open(self.RESOURCE_HEALTH_VIEW_PATH, 'w+') as fp:
                json.dump(self._resource_health_view, fp,  indent=4)

        except Exception as e:
            print("Error in writing resource health view file: {0}".format(e))
            return False

    def build_health_view_node_server_cache(self, category):

        try:
            node_health_json = self._resource_health_view['cluster']['sites']\
                                                [self.SITE_ID]['rack'][self.RACK_ID]\
                                                ['nodes'][self.NODE_ID]['node_server_1']
        except Exception as e:
            print("Error while extracting values from health view json % : " % e)
            return False

        if category == 'hw':
            hw_data = self.build_ipmi_fru_instances(self.ipmi_fru_lst)
            for fru in self.ipmi_fru_lst:
                fru_data = node_health_json['hw']['fru'][fru+'s']
                fru_data.update({"health": "", fru+"s_info": hw_data[fru]})

        elif category == 'platform_sensors':
            ps_data = self.build_ipmi_sensor_instances(self.sensor_list)
            for fru in self.sensor_list:
                fru_data = node_health_json['platform_sensors'][fru]
                fru_data.update({"health": "", fru+"_info": ps_data[fru]})

        try:
            with open(self.RESOURCE_HEALTH_VIEW_PATH, 'w+') as fp:
                json.dump(self._resource_health_view, fp,  indent=4)

        except Exception as e:
            print("Error in writing resource health view file: {0}".format(e))
            return False


    def build_encl_disks_cache(self):
        """Retreive realstor disk info using cli api /show/disks"""
        disks_existing_cache = True
        if self.sspl_service_status == 0:
            disks_existing_cache = True

        elif realstor_enclosure.check_prcache(self.storage_encl_dir+'disks/'):
            disks_existing_cache = False

        disk_data = {}
        drives = realstor_enclosure._get_realstor_show_data("drives")

        for drive in drives:
            slot = drive.get("slot", -1)

            if slot != -1:
                resource_id = drive.get("durable-id")
                durable_id = resource_id
                health = drive.get("health", "NA")
                disk_data.update({
                    self.encl_disk_resource_type+'-'+resource_id: {
                        "alert_type": "NA",
                        "severity": "NA",
                        "alert_uuid": "NA",
                        "durable_id": durable_id,
                        "health": health,
                        "fetch_time" : int(time.time())
                    }
                    })
                if not disks_existing_cache:
                    dcache_path = self.encl_disks_filename + \
                                     "disk_{0}.json".format(slot)
                    store.put(drive, dcache_path)
        return disk_data

    def build_encl_psus_cache(self):

        psus_existing_cache = True
        if self.sspl_service_status == 0:
            psus_existing_cache = True

        elif realstor_enclosure.check_prcache(self.storage_encl_dir+'psus/'):
            psus_existing_cache = False

        psu_data = {}
        psus_dict = {}

        psus = realstor_enclosure._get_realstor_show_data("power-supplies")

        for psu in psus:
            resource_id = psu.get("durable-id")
            durable_id = resource_id
            health = psu.get("health", "NA")
            psu_data.update({
                    self.encl_psu_resource_type+'-'+resource_id: {
                        "alert_type": "NA",
                        "severity": "NA",
                        "alert_uuid": "NA",
                        "durable_id": durable_id,
                        "health": health,
                        "fetch_time" : int(time.time())
                    }
            })
            if not psus_existing_cache:
                alert_type = ""
                if health != 'OK':
                    psus_dict.update({durable_id:{'health':health.lower(),
                                                  'alert_type':alert_type}})
        if not psus_existing_cache:
            store.put(psus_dict, self.encl_psus_filename)

        return psu_data

    def build_encl_controllers_cache(self):

        controllers_existing_cache = True
        if self.sspl_service_status == 0:
            controllers_existing_cache = True

        elif realstor_enclosure.check_prcache(self.storage_encl_dir+'controllers/'):
            controllers_existing_cache = False

        controller_data = {}
        controllers_dict = {}

        controllers = realstor_enclosure._get_realstor_show_data("controllers")

        for controller in controllers:
            resource_id = controller.get("durable-id")
            durable_id = resource_id
            health = controller.get("health", "NA")
            controller_data.update({
                    self.encl_controller_resource_type+'-'+resource_id: {
                        "alert_type": "NA",
                        "severity": "NA",
                        "alert_uuid": "NA",
                        "durable_id": durable_id,
                        "health": health,
                        "fetch_time" : int(time.time())
                    }
            })
            if not controllers_existing_cache:
                alert_type = ""
                if health != 'OK':
                    controllers_dict.update({durable_id:{'health':health.lower(),
                                                         'alert_type':alert_type}})
        if not controllers_existing_cache:
            store.put(controllers_dict, self.encl_controllers_filename)
        return controller_data

    def build_encl_fans_cache(self):

        fans_existing_cache = True
        if self.sspl_service_status == 0:
            fans_existing_cache = True

        elif realstor_enclosure.check_prcache(self.storage_encl_dir+'fanmodules/'):
            fans_existing_cache = False

        fan_data = {}
        fans_dict = {}

        fans = realstor_enclosure._get_realstor_show_data("fan-modules")

        for fan in fans:
            resource_id = fan.get("durable-id")
            durable_id = resource_id
            health = fan.get("health", "NA")
            fan_data.update({
                    self.encl_fan_resource_type+'-'+resource_id: {
                        "alert_type": "NA",
                        "severity": "NA",
                        "alert_uuid": "NA",
                        "durable_id": durable_id,
                        "health": health,
                        "fetch_time" : int(time.time())
                    }
            })
            if not fans_existing_cache:
                alert_type = ""
                if health != 'OK':
                    fans_dict.update({durable_id:alert_type})

        if not fans_existing_cache:
            store.put(fans_dict, self.encl_fans_filename)

        return fan_data

    def build_encl_sideplane_expander_cache(self):

        spln_existing_cache = True
        if self.sspl_service_status == 0:
            spln_existing_cache = True

        elif realstor_enclosure.check_prcache(self.storage_encl_dir+'sideplane_expanders/'):
            spln_existing_cache = False

        spln_data = {}
        sideplane_dict = {}
        sideplane_expanders = []

        encl_info = realstor_enclosure._get_realstor_show_data("enclosures")
        encl_drawers = encl_info[0]["drawers"]
        if encl_drawers:
            for drawer in encl_drawers:
                sideplane_list = drawer["sideplanes"]
                for sideplane in sideplane_list:
                     sideplane_expanders.append(sideplane)

        for spln in sideplane_expanders:
            resource_id = spln.get("durable-id")
            durable_id = resource_id
            health = spln.get("health", "NA")
            spln_data.update({
                    self.encl_sideplane_resource_type+'-'+resource_id: {
                        "alert_type": "NA",
                        "severity": "NA",
                        "alert_uuid": "NA",
                        "durable_id": durable_id,
                        "health": health,
                        "fetch_time" : int(time.time())
                    }
            })
            if not spln_existing_cache:
                alert_type = ""
                if health != 'OK':
                    sideplane_dict.update({durable_id:alert_type})

        if not spln_existing_cache:
            store.put(sideplane_dict, self.encl_sideplane_exp_filename)

        return spln_data

    def build_encl_logical_volume_cache(self):

        logvol_existing_cache = True
        if self.sspl_service_status == 0:
            logvol_existing_cache = True

        elif realstor_enclosure.check_prcache(self.storage_encl_dir+'logical_volumes/'):
            logvol_existing_cache = False

        logvol_data = {}
        logicalvolume_dict = {}

        diskgroups = realstor_enclosure._get_realstor_show_data("disk-groups")
        logicalvolumes = realstor_enclosure._get_realstor_show_data("volumes")

        for logicalvolume in logicalvolumes:
            resource_id = logicalvolume.get("volume-name", "NA")
            durable_id = logicalvolume.get("virtual-disk-serial", "NA")
            health = logicalvolume.get("health", "NA")
            logvol_data.update({
                    self.encl_logical_volume_resource_type+'-'+resource_id: {
                        "alert_type": "NA",
                        "severity": "NA",
                        "alert_uuid": "NA",
                        "durable_id": durable_id,
                        "health": health,
                        "fetch_time" : int(time.time())
                    }
            })
        if not logvol_existing_cache:
            for diskgroup in diskgroups:
                health = diskgroup.get("health", "NA")
                if health != 'OK':
                    serial_number = diskgroup.get("serial-number") # Disk Group Serial Number
                    alert_type = ""
                    logicalvolume_dict.update({serial_number:{'health':health.lower(),
                                                              'alert_type':alert_type}})

            store.put(logicalvolume_dict, self.encl_logical_volumes_filename)
        return logvol_data

    def build_encl_sas_port_instances(self):

        sas_data = {}
        sas_ports = realstor_enclosure._get_realstor_show_data("sas-link-health")

        for sas_port in sas_ports:
            resource_id = sas_port.get("durable-id")
            durable_id = resource_id
            health = sas_port.get("health", "NA")
            sas_data.update({
                    self.encl_sas_resource_type+'-'+resource_id: {
                        "alert_type": "NA",
                        "severity": "NA",
                        "alert_uuid": "NA",
                        "durable_id": durable_id,
                        "health": health,
                        "fetch_time" : int(time.time())
                    }
            })

        return sas_data

    def build_encl_platform_sensors_instances(self, platform_sensors):

        sensors_data = {}

        sensors = realstor_enclosure._get_realstor_show_data("sensor-status")

        for platform_sensor in platform_sensors:
            resource_type = "enclosure:sensor:{0}".format(platform_sensor)
            plsn_data = {}
            for sensor in sensors:
                if sensor['sensor-type'].lower() == platform_sensor:
                    resource_id = sensor.get("durable-id")
                    durable_id = resource_id
                    health = sensor.get("status", "NA")
                    plsn_data.update({
                            resource_type+'-'+resource_id: {
                                "alert_type": "NA",
                                "severity": "NA",
                                "alert_uuid": "NA",
                                "durable_id": durable_id,
                                "health": health,
                                "fetch_time" : int(time.time())
                            }
                    })

            sensors_data.update({platform_sensor: plsn_data})

        return sensors_data

    def build_system_persistent_cache(self):
        """Retreive realstor system state info using cli api /show/system"""

        system_existing_cache = True
        if self.sspl_service_status == 0:
            system_existing_cache = True

        elif realstor_enclosure.check_prcache(realstor_enclosure.system_persistent_cache):
            system_existing_cache = False

        if not system_existing_cache:
            system = realstor_enclosure._get_realstor_show_data("system")[0]
            if system:
                # Check if fault exists
                # TODO: use self.FAULT_KEY in system: system.key() generates
                # list and find item in that.
                if not realstor_enclosure.FAULT_KEY in system.keys():
                    print("{0} Healthy, no faults seen".format(realstor_enclosure.EES_ENCL))
                    return

                # Extract system faults and build memcache_faults
                store.put(system[realstor_enclosure.FAULT_KEY],
                    realstor_enclosure.faults_persistent_cache)

    def build_ipmi_fru_instances(self, frus):
        """Get the fru information based on fru_type and instance"""

        fru_id_map = self._executor.get_fru_list_by_type(
            ['Fan', 'Power Supply', 'Drive Slot / Bay'],
            sensor_id_map={})
        response = {}
        for fru in frus:
            resource_type = "node:fru:{0}".format(fru)
            fru_data = {}
            try:
                fru_type = self.NODE_REQUEST_MAP.get(fru)
                fru_dict = fru_id_map[fru_type]
                for sensor_id in fru_dict.values():
                    if fru == 'fan':
                        fru_data.update({
                        resource_type+'-'+sensor_id:{
                            "alert_type": "NA",
                            "severity": "NA",
                            "alert_uuid": "NA",
                            "durable_id": "NA",
                            "health": "NA",
                            "fetch_time" : int(time.time())
                        }})
                        continue
                    if sensor_id == '':
                        continue
                    common, sensor_specific_info = self._executor.get_sensor_props(sensor_id)
                    # Converting Fru ID From "HDD 0 Status (0xf0)" to "Drive Slot / Bay #0xf0"
                    resource_id = fru_type+" #"+common['Sensor ID'].split('(')[1][:-1]
                    fru_data.update({
                        resource_type+'-'+resource_id:{
                            "alert_type": "NA",
                            "severity": "NA",
                            "alert_uuid": "NA",
                            "durable_id": "NA",
                            "health": "NA",
                            "fetch_time" : int(time.time())
                        }})
            except KeyError as e:
                print('IPMIHealthView, _get_ipmi_fru_instances, \
                                Unable to process the FRU type: %s' % e)
                return response
            except Exception as e:
                print('IPMIHealthView, _get_ipmi_fru_instances, \
                                Error occured during request parsing %s' % e)
                return response

            response.update({fru: fru_data})
        return response

    def build_ipmi_sensor_instances(self, sensors):
        """Get the sensor information based on sensor_type and instance"""

        sensor_id_map = self._executor.get_fru_list_by_type(
            self.sensor_list,
            sensor_id_map={})
        response = {}
        for sensor in sensors:
            resource_type = "node:sensor:{0}".format(sensor)
            sensor_data = {}
            response.update({sensor: sensor_data})
            try:
                sensor_dict = sensor_id_map[sensor]
                for sensor_id in sensor_dict.values():
                    if sensor_id == '':
                        continue
                    sensor_data.update({
                        resource_type+'-'+sensor_id:{
                            "alert_type": "NA",
                            "severity": "NA",
                            "alert_uuid": "NA",
                            "durable_id": "NA",
                            "health": "NA",
                            "fetch_time" : int(time.time())
                        }})
            except KeyError as e:
                print('IPMIHealthView, _get_ipmi_sensor_instances, \
                                Unable to process the Sensor type: %s' % e)
                return response
            except Exception as e:
                print('IPMIHealthView, _get_ipmi_sensor_instances, \
                                Error occured during request parsing %s' % e)
                return response

            response.update({sensor: sensor_data})
        return response


sspl_health_view = SSPLHealthView()
sspl_health_view.build_health_view_storage_encl_cache('hw')
sspl_health_view.build_health_view_storage_encl_cache('sw')
sspl_health_view.build_health_view_storage_encl_cache('interfaces')
sspl_health_view.build_health_view_storage_encl_cache('platform_sensors')
sspl_health_view.build_health_view_node_server_cache('hw')
sspl_health_view.build_health_view_node_server_cache('platform_sensors')
