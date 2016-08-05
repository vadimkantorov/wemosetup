# wemosetup
A simple Python script to setup WeMo devices supporting:
 - connecting to a home Wi-Fi network (via calling a SOAP method ConnectHomeNetwork)
 - showing a list of discovered devices (via SSDP)
 - working on Windows too

I have tested it with WeMo Insight and WeMo Bridge.

# Examples

> $ python wemosetup.py discover

```
Discovering WeMo devices

Discovered:
 - WeMo Bridge (10.22.22.1:49152)
```
<br/>

> $ python wemosetup.py connecthomenetwork --ssid \<mywifinetworkname> --password \<mywifinetworkpassword>

```
Discovering WeMo devices

Discovered:
 - WeMo Bridge (10.22.22.1:49152)

Connecting discovered devices to network "<mywifinetworkname>"

 - WeMo Bridge (10.22.22.1:49152) ... [ok]

```
# Dependencies
- Python 2.7
- openssl (or openssl.exe) binary discoverable in system $PATH

# TODO
 - support getting end devices
 - support adding end devices
 - support switching state of end devices
 - support switching / displaying binary state for Insight
 - try/catch around all network calls

# Credits
1. https://web.archive.org/web/20130429034218/http://www.mgalisa.com/?p=91
2. https://github.com/issackelly/wemo
3. https://gist.github.com/hardillb/ffa9b458109fb8af7d0f#file-wemo-control-js
