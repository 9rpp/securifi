## Securifi RESTful API integration for Home Assistant

:warning: **experimental** :warning:

This is really a custom implementation of the Securifi websocket APIs to fulfill my own personal need at home, expect minimal function and limited quality from this integration. 

#### Install with HACS (Home Assistant Community Store)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

I recommend using [HACS](https://github.com/custom-components/hacs#hacs-home-assistant-community-store) to install and update this custom component.

In HACS Settings --> Custom Repositories, add the following:
```    
https://github.com/9rpp/securifi
```
Use type: `Integration`


#### Configuration

This integration is configured from the Home Assistant UI (Configuration -> Integrations -> '+' sign to add)

TODO - add screenshot

#### References
Securifi Websocket API Documentation: https://wiki.securifi.com/index.php/Websockets_Documentation#Updatedeviceindex
Securifi Device List Documentation: https://wiki.securifi.com/index.php/Devicelist_Documentation
