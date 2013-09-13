"""
Views related to operations on course objects
"""
import json
import time
import hashlib
import urllib2
from xml.etree import ElementTree
from django.http import HttpResponse

import logging
log = logging.getLogger(__name__)

__all__ = ['videoid2source']

USERID = '44B36C7761D3412F'
APIKEY = 'bySAR5lIFZEx08SKoYLQfNGjZMGx71cQ'

def encrypt(queryString):
	query = {}
	for s in queryString.split('&'):
		query[s.split('=')[0]] = s.split('=')[1]
	keys = query.keys()
	keys.sort()
	qs = [(key + '=' + query[key]) for key in keys]
	qs.append('time=' + str(int(time.time())))
	qf = '&'.join(qs)
	qf += '&hash=' + hashlib.md5(qf + '&salt=' + APIKEY).hexdigest().lower()
	return qf

def videoid2source(request, videoid):
	queryString = 'userid=' + USERID + '&videoid=' + videoid
	request_url = 'http://union.bokecc.com/api/mobile?' + encrypt(queryString)
	response = urllib2.urlopen(request_url)
	xmlString = response.read()

	sources = {
		'quality10': [],
		'quality20': []
	}

	try:
		tree = ElementTree.fromstring(xmlString)
		for element in tree.iter():
			if element.tag == "copy":
				quality = element.get('quality')
				source = element.text.split('?')[0] 
				if quality == '10':
					sources['quality10'].append(source)
				elif quality == '20':
					sources['quality20'].append(source)
	except Exception as e:
		logging.debug("error parsing video source")
		pass

	return HttpResponse(json.dumps({'sources': sources}), mimetype="application/json")
