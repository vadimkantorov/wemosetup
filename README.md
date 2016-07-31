# wemosetup
A simple Python script to setup WeMo devices supporting:
 - connecting to a home Wi-Fi network ("ConnectHomeNetwork")
 - showing a list of discovered devices

# Examples

> $ python wemosetup.py discover

```
Discovering WeMo devices

Discovered:
 - WeMo Bridge (10.22.22.1:49152)
```
 


> $ python wemosetup.py connecthomenetwork --ssid <mywifinetworkname> --password <mywifinetworkpassword>

```
Discovering WeMo devices

Discovered:
 - WeMo Bridge (10.22.22.1:49152)

Connecting discovered devices to network "<mywifinetworkname>"

 - WeMo Bridge (10.22.22.1:49152) ... [ok]

```

I have tested it with WeMo Insight and WeMo Bridge.

# TODO
 - support getting end devices
 - support adding end devices
 - support switching state of end devices
 - support switching / displaying binary state for Insight
