''' people export'''

import hashlib
import time
import urllib #for url encoding
import urllib2 #for sending requests
import base64
from random import uniform
try:
	import json
except ImportError:
	import simplejson as json

class Mixpanel(object):

    def __init__(self, api_key, api_secret, token):
        self.api_key = api_key
        self.api_secret = api_secret
        self.token = token

    def request(self, params, format = 'json'):
        '''let's craft the http request'''
        params['api_key']=self.api_key
        params['expire'] = int(time.time())+600 # 600 is ten minutes from now
        if 'sig' in params: del params['sig']
        params['sig'] = self.hash_args(params)

        request_url = 'http://mixpanel.com/api/2.0/engage/?' + self.unicode_urlencode(params)

        request = urllib.urlopen(request_url)
        data = request.read()

        #print request_url

        return data

    def hash_args(self, args, secret=None):
        '''Hash dem arguments in the proper way
        join keys - values and append a secret -> md5 it'''

        for a in args:
            if isinstance(args[a], list): args[a] = json.dumps(args[a])

        args_joined = ''
        for a in sorted(args.keys()):
            if isinstance(a, unicode):
                args_joined += a.encode('utf-8')
            else:
                args_joined += str(a)

            args_joined += "="

            if isinstance(args[a], unicode):
                args_joined += args[a].encode('utf-8')
            else:
                args_joined += str(args[a])

        hash = hashlib.md5(args_joined)

        if secret:
            hash.update(secret)
        elif self.api_secret:
            hash.update(self.api_secret)
        return hash.hexdigest()

    def unicode_urlencode(self, params):
        ''' Convert stuff to json format and correctly handle unicode url parameters'''

        if isinstance(params, dict):
            params = params.items()
        for i, param in enumerate(params):
            if isinstance(param[1], list):
                params[i] = (param[0], json.dumps(param[1]),)

        result = urllib.urlencode([(k, isinstance(v, unicode) and v.encode('utf-8') or v) for k, v in params])
        return result

    def update(self, userlist, uparams):
        url = "http://api.mixpanel.com/engage/"
        batch = []
        for user in userlist:
            distinctid = json.loads(user)['$distinct_id']
            tempparams = {
                    'token':self.token,
                    '$distinct_id':distinctid,
                    '$set': {'$AB random integer': str(round(uniform(1,100)))}
                    }
            tempparams.update(uparams)
            batch.append(tempparams)

        payload = {"data":base64.b64encode(json.dumps(batch)), "verbose":1,"ip":0,"api_key":self.api_key}

        response = urllib2.urlopen(url, urllib.urlencode(payload))
        message = response.read()

        '''if something goes wrong, this will say what'''
        if json.loads(message)['status'] != 1:
            print message

    def batch_update(self, filename, params):

        with open(filename,'r') as f:
            users = f.readlines()
        counter = len(users) // 100
        while len(users):
            batch = users[:1]
            self.update(batch, params)
            if len(users) // 100 != counter:
                counter = len(users) // 100
                print "%d users left!" % len(users)
            users = users[1:]


if __name__ == '__main__':
    api = Mixpanel(
        api_key = '',
        api_secret = '',
        token = ''
    )
    '''Here is the place to define your selector to target only the users that you're after'''
    '''parameters = {'selector':'(properties["$email"] == "Albany") or (properties["$city"] == "Alexandria")'}'''
    parameters = {'selector':''}
    response = api.request(parameters)
    
    parameters['session_id'] = json.loads(response)['session_id']
    parameters['page']=0
    global_total = json.loads(response)['total']
    
    print "Session id is %s \n" % parameters['session_id']
    print "Here are the # of people %d" % global_total
    fname = "output_people.txt"
    has_results = True
    total = 0
    with open(fname,'w') as f:
        while has_results:
            responser = json.loads(response)['results']
            total += len(responser)
            has_results = len(responser) == 1000
            for data in responser:
                f.write(json.dumps(data)+'\n')
            print "%d / %d" % (total,global_total)
            parameters['page'] += 1
            if has_results:
                response = api.request(parameters)

    print "All users being updated! Commencing to update: %s users" % total
    print response
    api.batch_update(fname, {'$ignore_time': "true"})
