# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Common settings and connection objects for 1&1 Cloud Server API
"""
import warnings

from libcloud.utils.py3 import httplib, parse_qs, urlparse

from libcloud.common.base import BaseDriver
from libcloud.common.base import ConnectionUserAndKey, ConnectionKey
from libcloud.common.base import JsonResponse
from libcloud.common.types import InvalidCredsError


class OneAndOne_v1_Response(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_error(self):
        if self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            raise InvalidCredsError(body['message'])
        else:
            body = self.parse_body()
            if 'message' in body:
                error = '%s (code: %s)' % (body['message'], self.status)
            else:
                error = body
            return error

    def success(self):
        return self.status in self.valid_response_codes


class OneAndOne_v1_Connection(ConnectionKey):
    """
    Connection class for the 1And1 (v1) driver.
    """

    host = 'cloudpanel-api.1and1.com'
    responseCls = OneAndOne_v1_Response

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request

        This method adds ``token`` to the request.
        """
        headers['X-token'] = self.key
        headers['Content-Type'] = 'application/json'
        return headers


class OneAndOneBaseDriver(BaseDriver):
    """
    1And1 BaseDriver
    """
    name = '1And1'
    website = 'https://www.1and1.co.uk'

    def __new__(cls, key, secret=None, api_version='v2', *args, **kwargs):
        if cls is OneAndOneBaseDriver:
            cls = OneAndOne_v1_BaseDriver
        else:
            raise  NotImplemented('Unsupported API version: %s' %
                                          (api_version))
        return super(OneAndOneBaseDriver, cls).__new__(cls, **kwargs)


class OneAndOne_v1_BaseDriver(OneAndOneBaseDriver):
    """
    1And1 BaseDriver using v1 of the API.

    Supports `ex_per_page` ``int`` value keyword parameter to adjust per page
    requests against the API.
    """
    connectionCls = OneAndOne_v1_Connection

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, region=None, ex_per_page=200, **kwargs):
        self.ex_per_page = ex_per_page
        super(OneAndOne_v1_BaseDriver, self).__init__(key, **kwargs)
