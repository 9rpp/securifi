"""Platform for Securifi switch integration."""
import sys
import logging
import async_timeout
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from .py_securifi import *

from datetime import timedelta
from websocket import create_connection
from homeassistant.components.switch import (PLATFORM_SCHEMA, SwitchEntity)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

_LOGGER = logging.getLogger(__name__)

# Set polling interval
SCAN_INTERVAL = timedelta(seconds=10)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_USERNAME, default='admin'): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
})

async def fetch_switch_data():
    ws = create_connection("ws://192.168.1.101:7681/admin/third62")
    result = ws.recv()
    if not result:
        _LOGGER.error("Could not connect to Securifi Almond websocket")
#    rsp = eval(result)
#    if rsp['CommandType'] != "DynamicAlmondModeUpdated":
#        raise Exception("Unexpected server handshake")

    mii = "1234"
    cmd = "DeviceList"
    req = '{"MobileInternalIndex":"' + mii + '","CommandType":"'+ cmd +'"}'
    ws.send(req)
    result = ws.recv()
    ws.close()
#    if not result:
#        raise Exception("invalid result")
    rsp = eval(result)
#    if rsp['CommandType'] != cmd or rsp['MobileInternalIndex'] != mii:
#        raise Exception("Request and response mismatches")
    
    # Parse through rsp and grab only type 1 and 50 switches
    # get Data:FriendlyDeviceType, Data:Name, DeviceValues:1:Value
    devices = {} 
    for dev in rsp['Devices']:
        dev_type = rsp['Devices'][dev]['Data']['Type']
        if dev_type == "1" or dev_type == "50":
            #print(rsp['Devices'][dev]['Data']['FriendlyDeviceType'])
            name = rsp['Devices'][dev]['Data']['Name']
            state = True if rsp['Devices'][dev]['DeviceValues']['1']['Value'].lower() == "true" else False
            devices[dev] = {"name": name, "state": state}
            #entities.append(SecurifiSwitch(coordinator, dev, name, state))

    return devices


#def setup_platform(hass, config, add_entities, discovery_info=None):
#async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Securifi platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    #host = config[CONF_HOST]
    #username = config[CONF_USERNAME]
    #password = config.get(CONF_PASSWORD)
    
    host = config_entry.data[CONF_HOST]
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

    almond = securifi_almond(host, password, user=username)

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
               #return await fetch_switch_data()
               return almond.get_switches()
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="SecurifiSwitch",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()
    
    entity = []
    #for dev in coordinator.data:
    #   entity.append(SecurifiSwitch(coordinator, str(dev), 
    #                                             coordinator.data[dev]["name"], 
    #                                             coordinator.data[dev]["state"]))
    for dev in coordinator.data:
       entity.append(SecurifiSwitch(coordinator, str(dev), 
                                                 coordinator.data[dev]["name"], 
                                                 coordinator.data[dev]["state"]))

    # Add devices
    #add_entities(entity)
    async_add_entities(entity)


class SecurifiSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Securifi switch (SecurifiSmartSwitch/BinarySwitch)."""
    """ https://wiki.securifi.com/index.php/Devicelist_Documentation """

    def __init__(self, coordinator, devid, name, state):
        """Initialize a Securifi switch."""
        super().__init__(coordinator)
        self._devid = devid
        self._name = name
        self._state = state

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the display name of this switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if light is on."""
        #return self._state
        return self.coordinator.data[self._devid]["state"]

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"securifi_almond_switch_{self._devid}"

    async def async_turn_on(self, **kwargs):
        """Instruct the switch to turn on.
        """
        ws = create_connection("ws://192.168.1.101:7681/admin/third62")
        result = ws.recv()
        mii = "1234"
        cmd = "UpdateDeviceIndex"
        req = '{"MobileInternalIndex":"' + mii + '","CommandType":"'+ cmd +'", "ID":"' + self._devid + '", "Index":"1", "Value":"true"}'
        ws.send(req)
        result = ws.recv()
        # '{"MobileInternalIndex":"321321","CommandType":"UpdateDeviceIndex","Success":"true"}'
        ws.close()
        if not result:
            raise Exception("invalid result from server")
        rsp = eval(result)
        if rsp['CommandType'] != cmd or rsp['MobileInternalIndex'] != mii:
            raise Exception("Request and response mismatches")

        if rsp['Success'].lower() == "true":
           self._state = True
        if rsp['Success'].lower() != "true":
            _LOGGER.error("Unable to turn on switch")

        #self._light.turn_on()
        await self.coordinator.async_request_refresh()


    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        ws = create_connection("ws://192.168.1.101:7681/admin/third62")
        result = ws.recv()
        mii = "1234"
        cmd = "UpdateDeviceIndex"
        req = '{"MobileInternalIndex":"' + mii + '","CommandType":"'+ cmd +'", "ID":"' + self._devid + '", "Index":"1", "Value":"false"}'
        ws.send(req)
        result = ws.recv()
        # '{"MobileInternalIndex":"321321","CommandType":"UpdateDeviceIndex","Success":"true"}'
        ws.close()
        if not result:
            raise Exception("invalid result from server")
        rsp = eval(result)
        if rsp['CommandType'] != cmd or rsp['MobileInternalIndex'] != mii:
            raise Exception("Request and response mismatches")

        if rsp['Success'].lower() == "true":
            self._state = False

        if rsp['Success'].lower() != "true":
            _LOGGER.error("Unable to turn off switch")

        #self._light.turn_off()
        await self.coordinator.async_request_refresh()

##    async def async_update(self):
##        """Fetch new state data for this light.
##        This is the only method that should fetch new data for Home Assistant.
##        """
##        ws = create_connection("ws://192.168.1.101:7681/admin/third62")
##        result = ws.recv()
##        mii = "1234"
##        cmd = "GetDeviceIndex"
##        req = '{"MobileInternalIndex":"' + mii + '","CommandType":"'+ cmd +'", "ID":"' + self._devid + '", "Index":"1"}'
##        ws.send(req)
##        result = ws.recv()
##        ws.close()
##        if not result:
##            raise Exception("invalid result from server")
##        rsp = eval(result)
##        if rsp['CommandType'] != cmd or rsp['MobileInternalIndex'] != mii:
##            raise Exception("Request and response mismatches")
##
##        if rsp['Success'].lower() == "true":
##            #_LOGGER.info("Securifi switch update() success " + str(self._devid) + "::" + str(rsp['Value']))
##            self._state = True if rsp['Value'].lower() == "true" else False
##        else:
##            _LOGGER.error("Securifi switch update() failed")
##
