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
1&1 Cloud Server Driver
"""
import json
import warnings

from libcloud.utils.iso8601 import parse_date
from libcloud.utils.py3 import httplib

from libcloud.common.oneandone import OneAndOne_v1_BaseDriver
from libcloud.common.digitalocean import DigitalOcean_v2_BaseDriver
from libcloud.common.types import InvalidCredsError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation, KeyPair
from libcloud.compute.base import Node, NodeDriver


class OneAndOneNodeDriver(NodeDriver):
    """
    1And1 NodeDriver defaulting to using APIv1.

    :keyword    key: Required for authentication. Used for ``v1``.
    :type       key: ``str``

    :keyword    secret: Used in driver authentication with key. Defaults to
                        None and when set, will cause driver to use ``v1`` for
                        connection and response. (optional)
    :type       secret: ``str``

    :keyword    api_version: Specifies the API version to use. ``v1`` and
                             ``v2`` are the only valid options. Defaults to
                             using ``v2`` (optional)
    :type       api_version: ``str``
    """
    type = Provider.ONE_AND_ONE
    name = '1And1'
    website = 'https://www.1and1.co.uk'

    def __new__(cls, key, secret=None, api_version='v1', **kwargs):
        if cls is OneAndOneNodeDriver:
            if key is None:
                raise InvalidCredsError(
                    'key missing for v1 authentication')
            cls = OneAndOne_v1_NodeDriver
        else:
            raise NotImplementedError('Unsupported API version: %s' %
                                      (api_version))
        return super(OneAndOneNodeDriver, cls).__new__(cls, **kwargs)


class OneAndOne_v1_NodeDriver(OneAndOne_v1_BaseDriver,
                                 OneAndOneNodeDriver):
    """
    1And1 NodeDriver using v1 of the API.
    """

    NODE_STATE_MAP = {'DEPLOYING': NodeState.PENDING,
                  'POWERED_OFF': NodeState.REBOOTING,
                  'POWERED_ON': NodeState.RUNNING}

    def list_nodes(self):
        data = self.connection.request('/v1/servers').parse_body()
        return list(map(self._to_node, data))

    def list_locations(self):
        data = self.connection.request('/v1/datacenters').parse_body()
        return list(map(self._to_location, data))

    def list_images(self):
        data = self.connection.request('/v1/server_appliances').parse_body()
        return list(map(self._to_image, data))

    def list_sizes(self):
        data = self.connection.request('/v1/servers/fixed_instance_sizes').parse_body()
        return list(map(self._to_size, data))

    def create_node(self, name, size, image, location=None):
        """
        Create a node.

        :keyword    ex_ssh_key_ids: A list of ssh key ids which will be added
                                   to the server. (optional)
        :type       ex_ssh_key_ids: ``list`` of ``str``

        :return: The newly created node.
        :rtype: :class:`Node`
        """
        hardware = {
            "fixed_instance_size_id": size.id
        }

        form = {"name": name, "description": "test", "hardware": hardware, "appliance_id": "7B9067380CB74BBDFE7F473DEEA2AF5C"}


        data = self.connection.request('/v1/servers', data=json.dumps(form), method='POST')

        # TODO: Handle this in the response class
        status = data.object.get('status', 'OK')
        if status == 'ERROR':
            message = data.object.get('message', None)
            error_message = data.object.get('error_message', message)
            raise ValueError('Failed to create node: %s' % (error_message))

        return self._to_node(data=data.object)

    def _to_node(self, data):
        extra_keys = ['backups_active', 'region_id', 'image_id', 'size_id']
        if 'status' in data:
            state = self.NODE_STATE_MAP.get(data['status']['state'], NodeState.UNKNOWN)
        else:
            state = NodeState.UNKNOWN

        if 'ips' in data and data['ips'] is not None:
            public_ips = [data['ips']]
        else:
            public_ips = []

        extra = {}
        for key in extra_keys:
            if key in data:
                extra[key] = data[key]

        node = Node(id=data['id'], name=data['name'], state=state,
                    public_ips=public_ips, private_ips=None, extra=extra,
                    driver=self)
        return node

    def _to_image(self, data):
        extra = {'os': data['os'], 'os_version': data['os_version'], 'architecture': data['architecture']}
        return NodeImage(id=data['id'], name=data['name'], extra=extra,
                         driver=self)

    def _to_location(self, data):
        return NodeLocation(id=data['id'], name=data['location'], country=data['country_code'],
                            driver=self)

    def _to_size(self, data):
        extra_keys = ['vcore', 'cores_per_processor']

        extra = {}

        if 'hardware' in data:
            hardware = data['hardware']
            ram = int(hardware['ram']) * 1024
            hdds_size = hardware['hdds'][0]['size']

            extra = {}
            for key in extra_keys:
                if key in hardware:
                    extra[key] = hardware[key]

        return NodeSize(id=data['id'], name=data['name'], ram=ram, disk=hdds_size,
                        bandwidth=0, price=0, driver=self, extra=extra)
