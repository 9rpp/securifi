"""An API Client to interact with Securifi Almond"""
import time
import json
import logging

from websocket import create_connection

_LOGGER = logging.getLogger(__name__)

#_LOGGER.setLevel(logging.DEBUG)
#ch = logging.StreamHandler()
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#ch.setFormatter(formatter)
#_LOGGER.addHandler(ch)

class securifi_almond():
    DEFAULT_PORT = 7681
    DEFAULT_USER = "admin"

    def __init__(self, host, pwd, port=DEFAULT_PORT, user=DEFAULT_USER):
        self._devlist = {}
        self._switches = []

        # Initiate API communication
        self._api_comm = self.api_comm(host, pwd, port, user)

        # Get initial list of switches
        sw_list = self.__get_switches()
        for sw in sw_list:
            self._switches.append(self.switch(self._api_comm, str(sw), sw_list[sw]['name'], sw_list[sw]['state']))
        #return self._switches

    def __get_devlist(self):
        _LOGGER.debug("__get_devlist")
        self._api_comm.open_conn()
        rsp = self._api_comm.send_cmd("1234", "DeviceList")
        if not rsp:
            _LOGGER.error("Unable to retrieve DeviceList")
            return False
        self._api_comm.close_conn()
        self._devlist = rsp
        return True


    # Queries devicelist and extract a list of switches
    def __get_switches(self):
        _LOGGER.debug("get_switches")
        self.__get_devlist()
        rsp = self._devlist
        
        # Parse through rsp and grab only type 1 and 50 switches
        # get Data:FriendlyDeviceType, Data:Name, DeviceValues:2:Value
        devices = {} 
        for dev in rsp['Devices']:
            dev_type = rsp['Devices'][dev]['Data']['Type']
            if dev_type == "1" or dev_type == "50":
                name = rsp['Devices'][dev]['Data']['Name']
                state = True if rsp['Devices'][dev]['DeviceValues']['1']['Value'].lower() == "true" else False
                devices[dev] = {"name": name, "state": state}

        return devices

    def get_devlist(self):
        return self._devlist

    def get_switches(self):
        return self._switches

    def refresh_switches(self):
        devs = self.__get_switches()
        for sw in self._switches:
            id = sw.get_devid()
            sw.set_name(devs[id]['name'])
            sw.set_state(devs[id]['state'])

    class api_comm:
        DEFAULT_PORT = 7681
        DEFAULT_USER = "admin"

        def __init__(self, host, pwd, port=DEFAULT_PORT, user=DEFAULT_USER):
            _LOGGER.debug("API __init__")
            self._host = host
            self._port = port
            self._user = user
            self._pwd = pwd
            self._ws = None

        def open_conn(self):
            url = "ws://" + self._host + ":" + str(self._port) + "/" + self._user + "/" + self._pwd
            _LOGGER.debug("open_conn: " + url)
            self._ws = create_connection(url)
            result = self._ws.recv()
            if not result:
                _LOGGER.error("Could not connect to Securifi Almond websocket")
                self._ws = None
                return False
            rsp = eval(result)
            if rsp['CommandType'] != "DynamicAlmondModeUpdated":
                _LOGGER.error("Unexpected server response from connection")
                self._ws = None
                return False
            return True


        def close_conn(self):
            _LOGGER.debug("close_conn")
            if not self._ws:
                _LOGGER.error("Invalid websocket, unable to close connection")
                return False
            self._ws.close()
            return True


        def send_cmd(self, mii, cmd, devid=None, idx=None, val=None):
            _LOGGER.debug("send_cmd: " + mii + "::" + cmd)
            if not mii or not cmd:
                _LOGGER.error("Invalid command params")
                return
            if not self._ws:
                _LOGGER.error("Websocket not established")
                return
            cmd_dict = {}
            cmd_dict["MobileInternalIndex"] = mii
            cmd_dict["CommandType"] = cmd
            if devid:
                cmd_dict["ID"] = str(devid)
            if idx:
                cmd_dict["Index"] = str(idx)
            if val:
                cmd_dict["Value"] = str(val).lower()
            req = json.dumps(cmd_dict)
            _LOGGER.debug("sending::" + req)
            self._ws.send(req)
            _LOGGER.debug("sent")
            result = self._ws.recv()
            _LOGGER.debug("received::" + result)
            if not result:
                _LOGGER.error("Invalid results")
                return
            rsp = eval(result)
            if rsp['CommandType'] != cmd or rsp['MobileInternalIndex'] != mii:
                _LOGGER.error("Request and response mismatches")
            return rsp


        def update_device(self, devid, idx, val=False):
            _LOGGER.debug("update_device: " + devid + "::" + idx + "::" + str(val))
            if not devid or not idx:
                _LOGGER.error("Invalid command params")
                return
            if not self._ws:
                _LOGGER.error("Websocket not established")
                return
            self.open_conn()
            rsp = self.send_cmd("1234", "UpdateDeviceIndex", devid, idx, str(val))
            self.close_conn()
            return True if rsp['Success'].lower() == "true" else False


    class switch:
        def __init__(self, api_comm, devid, name, state):
            self._api_comm = api_comm
            self._devid = devid
            self._name = name
            self._state = state
            self._idx = "1" # property index 1 is always the on/off for switches

        def print_attrib(self):
            _LOGGER.debug("devid::"+self._devid+", name::"+self._name+", state::"+str(self._state))

        def get_devid(self):
            return self._devid

        def get_name(self):
            return self._name

        def get_state(self):
            return self._state

        def set_name(self, name):
            _LOGGER.debug("Setting " + self._devid + " name to " + name)
            self._name = name

        def set_state(self, state):
            _LOGGER.debug("Setting " + self._devid + " state to " + str(state))
            self._state = state

        def turn_on(self):
            self._api_comm.update_device(self._devid, self._idx, True)

        def turn_off(self):
            self._api_comm.update_device(self._devid, self._idx, False)
    
def main():
    almond = securifi_almond("192.168.1.101", "third62")
    sw_objs = almond.get_switches()
    _LOGGER.debug(str(sw_objs))
    for sw in sw_objs:
        sw.print_attrib()

    _LOGGER.debug(">>>>>>  Turning off sw0")
    sw_objs[0].turn_off()
    for sw in sw_objs:
        sw.print_attrib()

    time.sleep(10)

    _LOGGER.debug(">>>>>> Turning on sw0 w/ refresh")
    sw_objs[0].turn_on()
    time.sleep(2)
    almond.refresh_switches()
    for sw in sw_objs:
        sw.print_attrib()

    time.sleep(10)

    _LOGGER.debug(">>>>>> Turning off sw0 w/ refresh")
    sw_objs[0].turn_off()
    time.sleep(2)
    almond.refresh_switches()
    for sw in sw_objs:
        sw.print_attrib()

if __name__ == "__main__":
    main()
