"""An API Client to interact with Securifi Almond"""
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
        self._host = host
        self._port = port
        self._user = user
        self._pwd = pwd
        self._ws = None
        self._devlist = {}


    def __open_conn(self):
        url = "ws://" + self._host + ":" + str(self._port) + "/" + self._user + "/" + self._pwd
        _LOGGER.debug("__open_conn: " + url)
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

    
    def __close_conn(self):
        _LOGGER.debug("__close_conn")
        if not self._ws:
            _LOGGER.error("Invalid websocket, unable to close connection")
            return False
        self._ws.close()
        return True


    def __send_cmd(self, mii, cmd):
        _LOGGER.debug("__send_cmd: " + mii + "::" + cmd)
        if not mii or not cmd:
            _LOGGER.error("Invalid command params")
            return 
        if not self._ws:
            _LOGGER.error("Websocket not established")
            return
        req = '{"MobileInternalIndex":"' + mii + '","CommandType":"'+ cmd +'"}'
        self._ws.send(req)
        _LOGGER.debug("sent")
        result = self._ws.recv()
        _LOGGER.debug("received")
        if not result:
            _LOGGER.error("Invalid results")
            return
        rsp = eval(result)
        if rsp['CommandType'] != cmd or rsp['MobileInternalIndex'] != mii:
            _LOGGER.error("Request and response mismatches")
        return rsp


    def __get_devlist(self):
        _LOGGER.debug("__get_devlist")
        self.__open_conn()
        rsp = self.__send_cmd("1234", "DeviceList")
        if not rsp:
            _LOGGER.error("Unable to retrieve DeviceList")
            return False
        self._devlist = rsp
        self.__close_conn()
        return True


    def get_all_devices(self):
        return self._devlist
    

    # Queries devicelist and extract a list of switches
    def get_switches(self):
        _LOGGER.debug("get_switches")
#        if not self._devlist:
#            self.__get_devlist()
# TODO: get switches from cache? 
        self.__get_devlist()
        rsp = self._devlist
        _LOGGER.debug(str(rsp))
        
        # Parse through rsp and grab only type 1 and 50 switches
        # get Data:FriendlyDeviceType, Data:Name, DeviceValues:2:Value
        devices = {} 
        for dev in rsp['Devices']:
            dev_type = rsp['Devices'][dev]['Data']['Type']
            if dev_type == "1" or dev_type == "50":
                #print(rsp['Devices'][dev]['Data']['FriendlyDeviceType'])
                name = rsp['Devices'][dev]['Data']['Name']
                state = True if rsp['Devices'][dev]['DeviceValues']['1']['Value'].lower() == "true" else False
                devices[dev] = {"name": name, "state": state}

        return devices
    
def main():
    almond = securifi_almond("192.168.1.101", "third62")
    all_sw = almond.get_switches()
    _LOGGER.debug(str(all_sw))

if __name__ == "__main__":
    main()
