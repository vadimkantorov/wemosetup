# wemosetup
A simple Python script to set up WeMo devices supporting:
 - connecting to a home Wi-Fi network (via calling a SOAP method ConnectHomeNetwork)
 - showing a list of discovered devices (via SSDP)
 - adding new bulbs to WeMo bridges, showing state of paired bulbs, removing bulbs
 - toggling state of WeMo switch and WeMo bridge devices
 - connecting to IFTTT
 - working on Windows too

I have tested it with WeMo Insight and WeMo Bridge.

# Examples

```shell
# Discover devices (with their IPs and ports)
python wemosetup.py discover

# Connect to home wi-fi
python wemosetup.py connecthomenetwork --ip 10.22.22.1 --port 49152 --ssid <mywifinetworkname> --password <mywifinetworkpassword>

# Add bulbs
python wemosetup.py addenddevices --ip 10.22.22.1 --port 49152

# List bulbs
python wemosetup.py getenddevices --ip 10.22.22.1 --port 49152

# Remove bulbs
python wemosetup.py removeenddevices --ip 10.22.22.1 --port 49152

# Reset bulbs (remove all bulbs and add all bulbs in one shot)
python wemosetup.py resetenddevices --ip 10.22.22.1 --port 49152

# Toggle bubls
python wemosetup.py toggle --ip 10.22.22.1 --port 49152

# Pair with IFTTT (will ask to follow a web link and then execute JavaScript from DevTools console), imei may be an arbitrary number 
python wemosetup.py ifttt --ip 10.22.22.1 --port 49152 --imei 123456789
```

# Resetting WeMo
WeMo devices are not very stable and may require resets of [bridges, switches](http://community.wemo.com/t5/WEMO-Application/WeMo-Resetting-the-Easy-Way/td-p/5016) and [bulbs](https://support.smartthings.com/hc/en-us/articles/204259040-Belkin-WeMo-LED-Bulb-F7C033-).

# Dependencies
- Python 2.7
- openssl (or openssl.exe) binary discoverable in system $PATH

# Credits and references
1. https://web.archive.org/web/20130429034218/http://www.mgalisa.com/?p=91
2. https://github.com/issackelly/wemo
3. https://gist.github.com/hardillb/ffa9b458109fb8af7d0f#file-wemo-control-js
4. https://github.com/pavoni/pywemo/blob/master/pywemo/ouimeaux_device/bridge.py
5. https://www.scip.ch/en/?labs.20160218
