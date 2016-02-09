# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import os.path
import six
import sys
import time

from oslo_log import log as logging
from tempest_lib import exceptions as lib_exc

from tempest.api.compute import base
from tempest.common.utils import data_utils
from tempest import config
from tempest import test

CONF = config.CONF
file_path='/tmp/tempest_temp_info_wXBQq8Vn'
LOG = logging.getLogger(__name__)


class IsolationTestSetup(base.BaseV2ComputeTest):

    credentials = ['primary']

    @classmethod
    def skip_checks(cls):
        super(IsolationTestSetup, cls).skip_checks()
        if not CONF.service_available.glance:
            raise cls.skipException('Glance is not available.')

    @classmethod
    def setup_credentials(cls):
        # No network resources required for this test
        cls.set_network_resources()
        super(IsolationTestSetup, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(IsolationTestSetup, cls).setup_clients()
        cls.client = cls.os.servers_client
        #cls.compute_images_client = cls.os.compute_images_client
        #cls.glance_client = cls.os.image_client
        #cls.keypairs_client = cls.os.keypairs_client
        #cls.security_client = cls.os.compute_security_groups_client
        #cls.rule_client = cls.os.compute_security_group_rules_client

    @classmethod
    def resource_setup(cls):
        super(IsolationTestSetup, cls).resource_setup()
        server = cls.create_test_server(wait_until='ACTIVE')
        cls.server = cls.client.show_server(server['id'])['server']

        '''
        name = data_utils.rand_name('image')
        body = cls.glance_client.create_image(name=name,
                                              container_format='bare',
                                              disk_format='raw',
                                              is_public=False)['image']
        image_id = body['id']
        image_file = six.StringIO(('*' * 1024))
        body = cls.glance_client.update_image(image_id,
                                              data=image_file)['image']
        cls.glance_client.wait_for_image_status(image_id, 'active')
        cls.image = cls.compute_images_client.show_image(image_id)['image']

        cls.keypairname = data_utils.rand_name('keypair')
        cls.keypairs_client.create_keypair(name=cls.keypairname)

        name = data_utils.rand_name('security')
        description = data_utils.rand_name('description')
        cls.security_group = cls.security_client.create_security_group(
            name=name, description=description)['security_group']

        parent_group_id = cls.security_group['id']
        ip_protocol = 'tcp'
        from_port = 22
        to_port = 22
        cls.rule = cls.rule_client.create_security_group_rule(
            parent_group_id=parent_group_id, ip_protocol=ip_protocol,
            from_port=from_port, to_port=to_port)['security_group_rule']
        '''

        f = open(file_path,'w')
        json.dump(server, f)
        f.close()

    @classmethod
    def resource_cleanup(cls):
        if hasattr(cls, 'image'):
            cls.compute_images_client.delete_image(cls.image['id'])
        if hasattr(cls, 'keypairname'):
            cls.keypairs_client.delete_keypair(cls.keypairname)
        if hasattr(cls, 'security_group'):
            cls.security_client.delete_security_group(cls.security_group['id'])
        super(IsolationTestSetup, cls).resource_cleanup()

    def test_wait_for_test_to_terminate(self):
        while os.path.exists(file_path):
            time.sleep(1)

##EOF
