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
import time
from oslo_log import log as logging
from tempest.api.compute import base
from tempest.common.utils import data_utils
from tempest import config
from tempest import test

CONF = config.CONF
LOG = logging.getLogger(__name__)
file_path = "/tmp/tempest_" + CONF.compute.image_ref

class UserIsolationSetup(base.BaseV2ComputeTest):

    credentials = ['primary']

    @classmethod
    def skip_checks(cls):
        super(UserIsolationSetup, cls).skip_checks()
        if not CONF.service_available.glance:
            raise cls.skipException('Glance is not available.')

    @classmethod
    def setup_credentials(cls):
        # No network resources required for this test
        cls.set_network_resources()
        super(UserIsolationSetup, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(UserIsolationSetup, cls).setup_clients()
        cls.client = cls.os.servers_client
        cls.compute_images_client = cls.os.compute_images_client
        cls.glance_client = cls.os.image_client
        cls.keypairs_client = cls.os.keypairs_client
        cls.security_client = cls.os.compute_security_groups_client
        cls.rule_client = cls.os.compute_security_group_rules_client

    @classmethod
    def resource_setup(cls):
        super(UserIsolationSetup, cls).resource_setup()

        fileinfo = {}
        if os.path.exists(file_path):
            LOG.info("/!\\ deleting previous file /!\\")
            os.remove(file_path)

        LOG.info("setting up server...")
        server = cls.create_test_server(wait_until='ACTIVE')

        LOG.info("server created and active")
        cls.server = cls.client.show_server(server['id'])['server']
        fileinfo['server'] = cls.server

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
        fileinfo['image'] = cls.image
        LOG.info("glance image created and active")

        cls.keypairname = data_utils.rand_name('keypair')
        fileinfo['keypairname'] = cls.keypairname
        cls.keypairs_client.create_keypair(name=cls.keypairname)
        LOG.info("keypair created")

        name = data_utils.rand_name('security')
        description = data_utils.rand_name('description')
        cls.security_group = cls.security_client.create_security_group(
            name=name, description=description)['security_group']
        fileinfo['security_group'] = cls.security_group
        LOG.info("security group created")

        parent_group_id = cls.security_group['id']
        ip_protocol = 'tcp'
        from_port = 22
        to_port = 22
        cls.rule = cls.rule_client.create_security_group_rule(
            parent_group_id=parent_group_id, ip_protocol=ip_protocol,
            from_port=from_port, to_port=to_port)['security_group_rule']
        fileinfo['rule'] = cls.rule
        LOG.info("security rule created")

        f = open(file_path, 'w')
        json.dump(fileinfo, f)
        f.close()
        LOG.info("file created with ids, waiting...")

    @classmethod
    def resource_cleanup(cls):
        if hasattr(cls, 'image'):
            cls.compute_images_client.delete_image(cls.image['id'])
        if hasattr(cls, 'keypairname'):
            cls.keypairs_client.delete_keypair(cls.keypairname)
        if hasattr(cls, 'security_group'):
            cls.security_client.delete_security_group(cls.security_group['id'])
        if os.path.exists(file_path):
            os.remove(file_path)
        if hasattr(cls, 'server'):
            cls.client.delete_server(cls.server['id'])
        super(UserIsolationSetup, cls).resource_cleanup()

    @test.idempotent_id('30d8f7d5-84cc-47e1-9ccd-e694ab86b685')
    def test_wait_for_test_to_terminate(self):
        while os.path.exists(file_path):
            time.sleep(3)

# EOF
