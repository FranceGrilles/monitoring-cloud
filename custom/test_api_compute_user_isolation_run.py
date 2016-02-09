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

import os.path
import json
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


class IsolationTestRun(base.BaseV2ComputeTest):

    credentials = ['primary']

    @classmethod
    def skip_checks(cls):
        super(IsolationTestRun, cls).skip_checks()
        if not CONF.service_available.glance:
            raise cls.skipException('Glance is not available.')

    @classmethod
    def setup_credentials(cls):
        # No network resources required for this test
        cls.set_network_resources()
        super(IsolationTestRun, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(IsolationTestRun, cls).setup_clients()
        cls.client = cls.os.servers_client

    @classmethod
    def resource_setup(cls):
        super(IsolationTestRun, cls).resource_setup()

        while not os.path.exists(file_path):
            time.sleep(1)
        f = open(file_path)
        server = json.load(f)
        f.close()

        cls.server = cls.client.show_server(server['id'])['server']

    @classmethod
    def resource_cleanup(cls):
        if hasattr(cls, 'image'):
            cls.compute_images_client.delete_image(cls.image['id'])
        if hasattr(cls, 'keypairname'):
            cls.keypairs_client.delete_keypair(cls.keypairname)
        if hasattr(cls, 'security_group'):
            cls.security_client.delete_security_group(cls.security_group['id'])
        os.remove(file_path)
        super(IsolationTestRun, cls).resource_cleanup()

###############################################################################

    def test_get_server_for_alt_account(self):
        self.assertTrue(self.client.show_server(self.server['id']))

    @test.attr(type=['negative'])
    def test_delete_server_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden, self.client.delete_server,
                          self.server['id'])

    def test_update_server_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden, self.client.update_server,
                          self.server['id'], name='test_update')

    def test_list_server_addresses_for_alt_account(self):
        self.assertTrue(self.client.list_addresses(self.server['id']))

    def test_list_server_addresses_by_network_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.list_addresses_by_network,
                          self.server['id'],
                          'public')

    def test_change_password_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden, self.client.change_password,
                          self.server['id'], adminPass='newpass')

    def test_reboot_server_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden, self.client.reboot_server,
                          self.server['id'], type='HARD')

    def test_rebuild_server_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden, self.client.rebuild_server,
                          self.server['id'], self.image_ref_alt)

    def test_resize_server_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden, self.client.resize_server,
                          self.server['id'], self.flavor_ref_alt)

    def test_create_image_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_compute_images_client.create_image,
                          self.server['id'], name='testImage')

    def test_create_server_with_unauthorized_image(self):
        self.assertRaises(lib_exc.BadRequest, self.client.create_server,
                          name='test', imageRef=self.image['id'],
                          flavorRef=self.flavor_ref)
    def test_create_server_fails_when_tenant_incorrect(self):
        # BUG(sdague): this test should fail because of bad auth url,
        # which means that when we run with a service catalog without
        # project_id in the urls, it should fail to fail, and thus
        # fail the test. It does not.
        #
        # The 400 BadRequest is clearly ambiguous, and something else
        # is wrong about this request. This should be fixed.
        #
        # A create server request should fail if the tenant id does not match
        # the current user
        # Change the base URL to impersonate another user
        self.client.auth_provider.set_alt_auth_data(
            request_part='url',
            auth_data=self.client.auth_provider.auth_data
        )
        self.assertRaises(lib_exc.BadRequest,
                          self.client.create_server, name='test',
                          imageRef=self.image['id'], flavorRef=self.flavor_ref)

    def test_get_keypair_of_alt_account_fails(self):
        # A GET request for another user's keypair should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_keypairs_client.show_keypair,
                          self.keypairname)

    def test_delete_keypair_of_alt_account_fails(self):
        # A DELETE request for another user's keypair should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_keypairs_client.delete_keypair,
                          self.keypairname)

    def test_get_image_for_alt_account_fails(self):
        # A GET request for an image on another user's account should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_compute_images_client.show_image,
                          self.image['id'])

    def test_delete_image_for_alt_account_fails(self):
        # A DELETE request for another user's image should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_compute_images_client.delete_image,
                          self.image['id'])

    def test_get_security_group_of_alt_account_fails(self):
        # A GET request for another user's security group should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_security_client.show_security_group,
                          self.security_group['id'])

    def test_delete_security_group_of_alt_account_fails(self):
        # A DELETE request for another user's security group should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_security_client.delete_security_group,
                          self.security_group['id'])

##EOF
