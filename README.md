# wemosetup
A simple Python script to set up WeMo devices supporting:
 - connecting to a home Wi-Fi network (via calling a SOAP method ConnectHomeNetwork)
 - showing a list of discovered devices (via SSDP)
 - adding new bulbs to WeMo bridges, showing state of paired bulbs
 - toggling state of WeMo switch and WeMo bridge devices
 - connecting to IFTTT
 - working on Windows too

I have tested it with WeMo Insight and WeMo Bridge.

# Examples

## Discover devices
```shell
$ python wemosetup.py discover

Discovering WeMo devices

Discovered:
 - WeMo Bridge (10.22.22.1:49152)
```

## Connect to home Wi-Fi
```shell
$ python wemosetup.py connecthomenetwork --host 10.22.22.1 --port 49152 --ssid \<mywifinetworkname> --password \<mywifinetworkpassword>


Device WeMo Bridge (10.22.22.1:49152) connceted to network "<mywifinetworkname>"

```

## Add bulbs
```shell
$ python wemosetup.py addenddevices --host 10.22.22.1 --port 49152

Paired bulbs: ['DEADBEEFBULBID']
```

## List bulbs
```shell
$ python wemosetup.py getenddevices --host 10.22.22.1 --port 49152

End devices of WeMo Bridge (192.168.0.25:49154)
 - 1234MYBULBID, state: off
```

## Toggle bulbs
```shell
$ python wemosetup.py toggle --host 10.22.22.1 --port 49152

WeMo Bridge (192.168.0.25:49154) toggled to: on
```

## Pair with IFTTT
```shell
$ python wemosetup.py ifttt --host 10.22.22.1 --port 49152 --imei 123456789

Navigate to the following address to complete pairing:
https://ifttt.com/wemo_activate?wemopin=GENERATED_MAGIC_WEMO_PIN&done_url=wemo://status=0

and run the following JavaScript code when you get to the webpage that says you need to open it from the WeMo app:
document.getElementById("WeMoAppMobileData").innerHTML = JSON.stringify({uniqueId:"SOME_ID_1", homeId:"SOME_ID_2", signature:"SOME_ID_3"}); doSubmit(1);
```

# Dependencies
- Python 2.7
- openssl (or openssl.exe) binary discoverable in system $PATH

# Credits and references
1. https://web.archive.org/web/20130429034218/http://www.mgalisa.com/?p=91
2. https://github.com/issackelly/wemo
3. https://gist.github.com/hardillb/ffa9b458109fb8af7d0f#file-wemo-control-js
4. https://github.com/pavoni/pywemo/blob/master/pywemo/ouimeaux_device/bridge.py
5. https://www.scip.ch/en/?labs.20160218
