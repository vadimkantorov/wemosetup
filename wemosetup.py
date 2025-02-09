import os
import io
import re
import sys
import time
import base64
import argparse
import subprocess
import itertools
import socket
import http.client
import urllib.request
import xml.dom.minidom
import binascii  # Import für hexlify

class SsdpDevice:
	def __init__(self, setup_xml_url, timeout=5):
		setup_xml_response = urllib.request.urlopen(setup_xml_url, timeout=timeout).read().decode()
		self.host_port = re.search(r'//(.+):(\d+)/', setup_xml_url).groups()
		parsed_xml = xml.dom.minidom.parseString(setup_xml_response)
		self.friendly_name = parsed_xml.getElementsByTagName('friendlyName')[0].firstChild.data
		self.udn = parsed_xml.getElementsByTagName('UDN')[0].firstChild.data
		self.services = {elem.getElementsByTagName('serviceType')[0].firstChild.data: elem.getElementsByTagName('controlURL')[0].firstChild.data for elem in parsed_xml.getElementsByTagName('service')}

	def soap(self, service_name, method_name, response_tag=None, args={}, timeout=30):
		service_type, control_url = [(service_type, control_url) for service_type, control_url in self.services.items() if service_name in service_type][0]
		service_url = 'http://{}:{}/'.format(*self.host_port) + control_url.lstrip('/')
		request_body = f'''<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"> <s:Body>  <u:{method_name} xmlns:u="{service_type}">   ''' + ''.join(itertools.starmap('<{0}>{1}</{0}>'.format, args.items())) + f'''  </u:{method_name}> </s:Body></s:Envelope>'''
		request_headers = {
			'Content-Type': 'text/xml; charset="utf-8"',
			'SOAPACTION': f'"{service_type}#{method_name}"',
			'Content-Length': len(request_body),
			'HOST': '{}:{}'.format(*self.host_port)
		}
		response = urllib.request.urlopen(urllib.request.Request(service_url, request_body.encode(), headers=request_headers), timeout=timeout).read().decode()
		if response_tag:
			response = xml.dom.minidom.parseString(response).getElementsByTagName(response_tag)[0].firstChild.data
		return response

	@staticmethod
	def discover_devices(service_type, timeout=5, retries=1, mx=3):
		host_port = ("239.255.255.250", 1900)
		message = "\r\n".join([
			'M-SEARCH * HTTP/1.1',
			'HOST: {0}:{1}',
			'MAN: "ssdp:discover"',
			'ST: {service_type}',
			'MX: {mx}', '', ''
		])
		socket.setdefaulttimeout(timeout)

		setup_xml_urls = []
		for _ in range(retries):
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
			sock.sendto(message.format(*host_port, service_type=service_type, mx=mx).encode(), host_port)
			while True:
				try:
					fake_socket = io.BytesIO(sock.recv(1024))
					fake_socket.makefile = lambda *args, **kwargs: fake_socket
					response = http.client.HTTPResponse(fake_socket)
					response.begin()
					setup_xml_urls.append(response.getheader('location'))
				except socket.timeout:
					break
		return setup_xml_urls

	def __str__(self):
		return '{} ({}:{})'.format(self.friendly_name, *self.host_port)


class WemoDevice(SsdpDevice):
	def __init__(self, host, port):
		SsdpDevice.__init__(self, f'http://{host}:{port}/setup.xml')

	@staticmethod
	def discover_devices(*args, **kwargs):
		return [re.search(r'//(.+):(\d+)/', setup_xml_url).groups() for setup_xml_url in SsdpDevice.discover_devices(service_type='urn:Belkin:service:basicevent:1', *args, **kwargs)]

	def encrypt_wifi_password(self, password, meta_array):
		keydata = meta_array[0][0:6] + meta_array[1] + meta_array[0][6:12]
		salt, iv = keydata[0:8], keydata[0:16]
		assert len(salt) == 8 and len(iv) == 16
		stdout, stderr = subprocess.Popen(['openssl', 'enc', '-aes-128-cbc', '-md', 'md5', '-S', salt.encode('utf-8').hex(), '-iv', iv.encode('utf-8').hex(), '-pass', 'pass:' + keydata], stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(password.encode())
		encrypted_password = base64.b64encode(stdout[16:])  # removing 16byte magic and salt prefix inserted by OpenSSL
		encrypted_password += (len(encrypted_password).to_bytes(1, 'big')) + (b'0' if len(password) < 16 else b'') + (len(password).to_bytes(1, 'big'))
		return encrypted_password

	def generate_auth_code(self, device_id, private_key):
		expiration_time = int(time.time()) + 200
		stdout, stderr = subprocess.Popen(['openssl', 'sha1', '-binary', '-hmac', private_key], stdin = subprocess.PIPE, stdout = subprocess.PIPE).communicate(f'{device_id}\n\n{expiration_time}')
		auth_code = "SDU {}:{}:{}".format(device_id, base64.b64encode(stdout).strip(), expiration_time)
		return auth_code
		
	def prettify_device_state(self, state):
		return 'on' if state == 1 else 'off' if state == 0 else f'unknown ({state})'

def discover():
	print()
	print('Discovery of WeMo devices')
	print()
	
	host_ports = set(WemoDevice.discover_devices() + [('10.22.22.1', str(port)) for port in range(49151, 49156)])
	discovered_devices = []
	for host, port in sorted(host_ports):
		try:
			discovered_devices.append(WemoDevice(host, port))
		except urllib.error.URLError:
			continue
			
	print('Discovered:' if discovered_devices else 'No devices discovered')
	for device in discovered_devices:
		print(' - ' + str(device))
	print()
	return discovered_devices

def connecthomenetwork(host, port, ssid, password, timeout = 10):
	device = WemoDevice(host, port)
	aps = [ap for ap in device.soap('WiFiSetup', 'GetApList', 'ApList').split('\n') if ap.startswith(ssid + '|')]
	if len(aps) == 0:
		print(f'Could not find network "{ssid}". Try again.')
		return
	elif len(aps) > 1:
		print(f'Discovered {len(aps)} networks with SSID "{ssid}", using the first available..."')
		
	channel, auth_mode, encryption_mode = re.match(r'.+\|(.+)\|.+\|(.+)/(.+),', aps[0]).groups()
	meta_array = device.soap('metainfo', 'GetMetaInfo', 'MetaInfo').split('|')
	connect_status = device.soap('WiFiSetup', 'ConnectHomeNetwork', 'PairingStatus', args = {
		'ssid' : ssid,
		'auth' : auth_mode, 
		'password' : device.encrypt_wifi_password(password, meta_array),
		'encrypt' : encryption_mode,
		'channel'  : channel
	})
	
	time.sleep(timeout)
	
	network_status = device.soap('WiFiSetup', 'GetNetworkStatus', 'NetworkStatus')
	close_status = device.soap('WiFiSetup', 'CloseSetup', 'status')
	print(f'Device failed to connect to the network: ({connect_status}, {network_status}). Try again.' if network_status not in ['1', '3'] or close_status != 'success' else f'Device {device} connected to network "{ssid}"')
	
def getenddevices(device = None, host = None, port = None, list_type = 'PAIRED_LIST'):
	device = device or WemoDevice(host, port)
	end_devices_decoded = device.soap('bridge', 'GetEndDevices', 'DeviceLists', args = {'DevUDN' : device.udn, 'ReqListType' : list_type}).replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
	end_devices = {str(elem.getElementsByTagName('DeviceID')[0].firstChild.data) : {'' : None, '1' : 1, '0' : 0}[elem.getElementsByTagName('CurrentState')[0].firstChild.data.split(',')[0]] for elem in xml.dom.minidom.parseString(end_devices_decoded).getElementsByTagName('DeviceInfo')} if end_devices_decoded != '0' else {}
	if host != None and port != None:
		print(f'End devices of {device}:' if end_devices else 'No end devices of {device} were found')
		for device_id, state in sorted(end_devices.items()):
			print(' - {}, state: {}'.format(device_id, device.prettify_device_state(state)))
	return end_devices
		
def addenddevices(host, port, timeout = 10):
	device = WemoDevice(host, port)
	
	device.soap('bridge', 'OpenNetwork', args = {'DevUDN' : device.udn})
	time.sleep(timeout)
	
	scanned_bulb_device_ids = getenddevices(device, list_type = 'SCAN_LIST').keys()	
	if scanned_bulb_device_ids:
		device.soap('bridge', 'AddDeviceName', args = {'DeviceIDs' : ','.join(scanned_bulb_device_ids), 'FriendlyNames' : ','.join(scanned_bulb_device_ids)})
		time.sleep(timeout)
		
	paired_bulb_device_ids = getenddevices(device, list_type = 'PAIRED_LIST').keys()
	device.soap('bridge', 'CloseNetwork', args = {'DevUDN' : device.udn})
	
	print('Paired bulbs: ', sorted(set(scanned_bulb_device_ids) & set(paired_bulb_device_ids)))
	
def removeenddevices(host, port, timeout = 10):
	device = WemoDevice(host, port)
	
	device.soap('bridge', 'OpenNetwork', args = {'DevUDN' : device.udn})
	time.sleep(timeout)
	
	scanned_bulb_device_ids = getenddevices(device, list_type = 'PAIRED_LIST').keys()	
	if scanned_bulb_device_ids:
		device.soap('bridge', 'RemoveDevice', args = {'DeviceIDs' : ','.join(scanned_bulb_device_ids), 'FriendlyNames' : ','.join(scanned_bulb_device_ids)})
		time.sleep(timeout)
		
	paired_bulb_device_ids = getenddevices(device, list_type = 'PAIRED_LIST').keys()
	device.soap('bridge', 'CloseNetwork', args = {'DevUDN' : device.udn})
	
	print('Bulbs removed:', sorted(scanned_bulb_device_ids), 'bulbs left:', sorted(paired_bulb_device_ids))

def resetenddevices(host, port, timeout = 30):
	removeenddevices(host, port, timeout = timeout)
	addenddevices(host, port, timeout = timeout)
	
def toggle(host, port):
	device = WemoDevice(host, port)
	if 'Bridge' in device.friendly_name:
		bulbs = getenddevices(device, list_type = 'PAIRED_LIST')
		new_binary_state = 1 - int(bulbs.items()[0][1] or 0)
		device.soap('bridge', 'SetDeviceStatus', args = {'DeviceStatusList' : 
			''.join(['<?xml version="1.0" encoding="utf-8"?>'] +
				['''<DeviceStatus><IsGroupAction>NO</IsGroupAction><DeviceID available="YES">{}</DeviceID><CapabilityID>{}</CapabilityID><CapabilityValue>{}</CapabilityValue></DeviceStatus>'''.format(bulb_device_id, 10006, new_binary_state) for bulb_device_id in bulbs.keys()]
			).replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
		})
	else:
		new_binary_state = 1 - int(device.soap('basicevent', 'GetBinaryState', 'BinaryState') == '1')
		device.soap('basicevent', 'SetBinaryState', args = {'BinaryState' : new_binary_state})
	
	print('{} toggled to: {}'.format(device, device.prettify_device_state(new_binary_state)))

def ifttt(host, port, device_id):
	device = WemoDevice(host, port)
	parse_xml = lambda resp, fields: [doc.getElementsByTagName(field)[0].firstChild.data for doc in [xml.dom.minidom.parseString(resp)] for field in fields]
	error = lambda status: f'{device} failed to enable IFTTT: status code {status}'
	
	home_id, private_key, remote_access_status = parse_xml(device.soap('remoteaccess', 'RemoteAccess', args = {'DeviceId' : device_id, 'DeviceName' : device_id, 'dst' : 0, 'HomeId' : '', 'MacAddr' : '', 'pluginprivateKey' : '', 'smartprivateKey' : '', 'smartUniqueId' : '', 'numSmartDev' : ''}), ['homeId', 'smartprivateKey', 'statusCode'])
	if remote_access_status != 'S':
		print(error(remote_access_status))
		return
		
	auth_code = device.generate_auth_code(device_id, private_key)
	activation_code, generate_pin_status = parse_xml(urllib.request.urlopen(urllib.request.Request(f'https://api.xbcs.net:8443/apis/http/plugin/generatePin/{home_id}/IFTTT', headers = {'Content-Type' : 'application/xml', 'Authorization' : auth_code})).read().decode(), ['activationCode', 'status'])
	if generate_pin_status != '0':
		print(error(generate_pin_status))
		return
	
	print('Navigate to the following address to complete pairing:')
	print(f'https://ifttt.com/wemo_activate?wemopin={activation_code}&done_url=wemo://status=0')
	print()
	print('and run the following JavaScript code when you get to the webpage that says you need to open it from the WeMo app:')
	print('document.getElementById("WeMoAppMobileData").innerHTML = JSON.stringify({' + f'uniqueId:"{device_id}", homeId:"{home_id}", signature:"{auth_code}"' + '}); doSubmit(1);')

if __name__ == '__main__':
	common = argparse.ArgumentParser(add_help = False)
	common.add_argument('--ip', required = True, dest = 'host')
	common.add_argument('--port', required = True, type = int)
	
	parser = argparse.ArgumentParser()
	subparsers = parser.add_subparsers()
	
	subparsers.add_parser('discover').set_defaults(func = discover)
	subparsers.add_parser('getenddevices', parents = [common]).set_defaults(func = getenddevices)
	subparsers.add_parser('addenddevices', parents = [common]).set_defaults(func = addenddevices)
	subparsers.add_parser('removeenddevices', parents = [common]).set_defaults(func = removeenddevices)
	subparsers.add_parser('resetenddevices', parents = [common]).set_defaults(func = resetenddevices)
	subparsers.add_parser('toggle', parents = [common]).set_defaults(func = toggle)
	
	cmd = subparsers.add_parser('connecthomenetwork', parents = [common])
	cmd.add_argument('--ssid', required = True)
	cmd.add_argument('--password', required = True)
	cmd.set_defaults(func = connecthomenetwork)
	
	cmd = subparsers.add_parser('ifttt', parents = [common])
	cmd.add_argument('--imei', required = True, type = int, dest = 'device_id')
	cmd.set_defaults(func = ifttt)
		
	args = vars(parser.parse_args())
	cmd = args.pop('func')
	cmd(**args)
