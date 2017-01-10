import re
import os
import sys
import time
import argparse
import subprocess
import urllib2
import itertools
import xml.dom.minidom
import httplib
import socket
import StringIO

class Device:
	def __init__(self, setup_xml_url, timeout = 5):
		setup_xml_response = urllib2.urlopen(setup_xml_url, timeout = timeout).read()
		self.host = os.path.dirname(setup_xml_url).split('//')[1]
		parsed_xml = xml.dom.minidom.parseString(setup_xml_response)
		self.friendly_name = parsed_xml.getElementsByTagName('friendlyName')[0].firstChild.data
		self.services = {elem.getElementsByTagName('serviceType')[0].firstChild.data : elem.getElementsByTagName('controlURL')[0].firstChild.data for elem in parsed_xml.getElementsByTagName('service')}
		
	def soap(self, service_name, method_name, response_tag = None, args = {}, timeout = 30):
		service_type, control_url = [(service_type, control_url) for service_type, control_url in self.services.items() if service_name in service_type][0]
		service_url = 'http://' + self.host + '/' + control_url.lstrip('/')
		request_body = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
 <s:Body>
  <u:%s xmlns:u="%s">
   %s
  </u:%s>
 </s:Body>
</s:Envelope>''' % (method_name, service_type, ''.join(itertools.starmap('<{0}>{1}</{0}>'.format, args.items())), method_name)
		request_headers = {
			'Content-Type' : 'text/xml; charset="utf-8"',
			'SOAPACTION' : '"%s#%s"' % (service_type, method_name),
			'Content-Length': len(request_body),
			'HOST' : self.host
		}
		response = urllib2.urlopen(urllib2.Request(service_url, request_body, headers = request_headers), timeout = timeout).read()
		if response_tag:
			response = xml.dom.minidom.parseString(response).getElementsByTagName(response_tag)[0].firstChild.data
		return response
		
	@staticmethod
	def discover_devices(service_type, timeout = 5, retries = 1, mx = 3):
	    host_port = ("239.255.255.250", 1900)
	    message = "\r\n".join([
	        'M-SEARCH * HTTP/1.1',
	        'HOST: {0}:{1}',
	        'MAN: "ssdp:discover"',
	        'ST: {service_type}','MX: {mx}','',''])
	    socket.setdefaulttimeout(timeout)
	    
	    setup_xml_urls = []
	    for _ in range(retries):
	        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
	        sock.sendto(message.format(*host_port, service_type=service_type, mx=mx), host_port)
	        while True:
	            try:
	            	fake_socket = StringIO.StringIO(sock.recv(1024))
	            	fake_socket.makefile = lambda *args, **kwargs: fake_socket
	            	response = httplib.HTTPResponse(fake_socket)
	            	response.begin()
	            	setup_xml_urls.append(response.getheader('location'))
	            except socket.timeout:
	                break
	    return setup_xml_urls
		
	def __str__(self):
		return '%s (%s)' % (self.friendly_name, self.host)

def discover():
	print ''
	print 'Discovering WeMo devices'
	print ''
	
	setup_xml_urls = sorted(set(Device.discover_devices('urn:Belkin:service:basicevent:1') + map('http://10.22.22.1:{0}/setup.xml'.format, range(49151, 49156))))
	discovered_devices = []
	for setup_xml_url in setup_xml_urls:
		try:
			discovered_devices.append(Device(setup_xml_url))
		except urllib2.URLError:
			continue
			
	if discovered_devices:
		print 'Discovered:'
		for device in discovered_devices:
			print ' - %s' % device
	else:
		print 'No devices discovered'
	print ''
	return discovered_devices

def connecthomenetwork(ssid, password):
	def encrypt_wifi_password(password, meta_array):
		keydata = meta_array[0][0:6] + meta_array[1] + meta_array[0][6:12]
		salt, iv = keydata[0:8], keydata[0:16]
		assert len(salt) == 8 and len(iv) == 16

		stdout, stderr = subprocess.Popen(['openssl', 'enc', '-aes-128-cbc', '-md', 'md5', '-S', salt.encode('hex'), '-iv', iv.encode('hex'), '-pass', 'pass:' + keydata], stdin = subprocess.PIPE, stdout = subprocess.PIPE).communicate(password)
		encrypted_password = stdout[16:].encode('base64') # removing 16byte magic and salt prefix inserted by OpenSSL
		encrypted_password += hex(len(encrypted_password))[2:] + ('0' if len(password) < 16 else '') + hex(len(password))[2:]
		return encrypted_password
	
	discovered_devices = discover()
	if len(discovered_devices) == 0:
		return
	
	print 'Connecting discovered devices to network "%s"' % ssid
	for device in discovered_devices:
		sys.stdout.write(' - %s ... ' % device)
		
		aps = [ap for ap in device.soap('WiFiSetup', 'GetApList', 'ApList').split('\n') if ap.startswith(ssid + '|')]
		if len(aps) != 1:
			print 'Could not find network "%s" (or found several networks with this name). Try again or adjust SSID.' % ssid
			continue
		channel, auth_mode, encryption_mode = re.match('.+\|(.+)\|.+\|(.+)/(.+),', aps[0]).groups()
		
		meta_array = device.soap('metainfo', 'GetMetaInfo', 'MetaInfo').split('|')
		encrypted_password = encrypt_wifi_password(password, meta_array)
			
		connect_status = device.soap('WiFiSetup', 'ConnectHomeNetwork', 'PairingStatus', args = {
			'ssid' : ssid,
			'auth' : auth_mode, 
			'password' : encrypted_password,
			'encrypt' : encryption_mode,
			'channel'  : channel
		})
		
		time.sleep(2)
		
		network_status = device.soap('WiFiSetup', 'GetNetworkStatus', 'NetworkStatus')
		close_status = device.soap('WiFiSetup', 'CloseSetup', 'status')
		if network_status not in ['1', '3'] or close_status != 'success':
			print 'Device failed to connect to the network: (%s, %s). Try again.' % (connect_status, network_status)
			continue
			
		print '[ok]'
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	subparsers = parser.add_subparsers()
	
	cmd = subparsers.add_parser('connecthomenetwork')
	cmd.add_argument('--ssid', required = True)
	cmd.add_argument('--password', required = True)
	cmd.set_defaults(func = connecthomenetwork)
	
	subparsers.add_parser('discover').set_defaults(func = discover)
	
	args = vars(parser.parse_args())
	cmd = args.pop('func')
	cmd(**args)
