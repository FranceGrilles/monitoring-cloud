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
import time

from oslo_log import log as logging
from tempest_lib import exceptions as lib_exc

from tempest.api.compute import base
from tempest import config
from tempest import test

CONF = config.CONF
file_path = '/tmp/ztempest_temp_info_wXBQq8Vn'
LOG = logging.getLogger(__name__)


class UserIsolationRun(base.BaseV2ComputeTest):

    credentials = ['primary']

    @classmethod
    def skip_checks(cls):
        super(UserIsolationRun, cls).skip_checks()
        if not CONF.service_available.glance:
            raise cls.skipException('Glance is not available.')

    @classmethod
    def setup_credentials(cls):
        # No network resources required for this test
        cls.set_network_resources()
        super(UserIsolationRun, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(UserIsolationRun, cls).setup_clients()
        cls.client = cls.os.servers_client
        cls.compute_images_client = cls.os.compute_images_client
        cls.glance_client = cls.os.image_client
        cls.keypairs_client = cls.os.keypairs_client
        cls.security_client = cls.os.compute_security_groups_client
        cls.rule_client = cls.os.compute_security_group_rules_client

    @classmethod
    def resource_setup(cls):
        super(UserIsolationRun, cls).resource_setup()

        LOG.info("waiting for setup to run...")
        while not os.path.exists(file_path):
            time.sleep(3)
        f = open(file_path)
        fileinfo = json.load(f)
        f.close()

        cls.server = fileinfo['server']
        cls.image = fileinfo['image']
        cls.keypairname = fileinfo['keypairname']
        cls.security_group = fileinfo['security_group']
        cls.rule = fileinfo['rule']

    @classmethod
    def resource_cleanup(cls):
        os.remove(file_path)
        super(UserIsolationRun, cls).resource_cleanup()

###############################################################################

    @test.idempotent_id('85a2b6ee-88fa-49b6-aa71-e75a97625366')
    def test_get_server_for_alt_account(self):
        self.assertTrue(self.client.show_server, self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('4407198c-9cb9-4e4a-a90c-40de5e3d6248')
    def test_update_server_for_alt_account_fails(self):
        # An update server request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.update_server,
                          self.server['id'], name='tempest_test_rename')

    @test.idempotent_id('3d09a432-f9bf-4ace-ba42-8c27f77018c4')
    def test_list_server_addresses_for_alt_account(self):
        self.assertTrue(self.client.list_addresses, self.server['id'])

    @test.idempotent_id('2117685c-bbee-4366-8234-a9061137d9cb')
    def test_list_server_addresses_by_network_for_alt_account(self):
        server_id = self.server['id']
        self.assertTrue(self.client.list_addresses_by_network, server_id)

    @test.attr(type=['negative'])
    @test.idempotent_id('fa1a0956-ca6f-4dbc-8874-32de1c2ce2e8')
    def test_change_password_for_alt_account_fails(self):
        # A change password request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.change_password,
                          self.server['id'], adminPass='newpass')

    @test.attr(type=['negative'])
    @test.idempotent_id('68cf02b8-42ca-4644-b3f5-b78347e01a45')
    def test_create_image_for_alt_account_fails(self):
        # A create image request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.compute_images_client.create_image,
                          self.server['id'], name='testImage')

    @test.attr(type=['negative'])
    @test.idempotent_id('6e3fa9de-bae3-48f8-8598-4edb8419924a')
    def test_create_server_with_unauthorized_image_fails(self):
        # Server creation with another user's image should fail
        self.assertRaises(lib_exc.BadRequest, self.client.create_server,
                          name='test', imageRef=self.image['id'],
                          flavorRef=self.flavor_ref)

    @test.attr(type=['negative'])
    @test.idempotent_id('f790ace9-6ffc-4bf2-a7a6-ed12fab7f08d')
    def test_get_keypair_of_alt_account_fails(self):
        # A GET request for another user's keypair should fail
        self.assertRaises(lib_exc.NotFound,
                          self.keypairs_client.show_keypair,
                          self.keypairname)

    @test.attr(type=['negative'])
    @test.idempotent_id('3dbaaf4f-5c33-4391-a4d9-1e17ca3c8a89')
    def test_delete_keypair_of_alt_account_fails(self):
        # A DELETE request for another user's keypair should fail
        self.assertRaises(lib_exc.NotFound,
                          self.keypairs_client.delete_keypair,
                          self.keypairname)

    @test.idempotent_id('7ca3b91e-5fc7-4c7e-8104-cfa678e932db')
    def test_get_image_for_alt_account(self):
        self.assertTrue(self.compute_images_client.show_image,
                        self.image['id'])

#    @test.attr(type=['negative'])
#    def test_delete_image_for_alt_account_fails(self):
#        # A DELETE request for another user's image should fail
#        self.assertRaises(lib_exc.NotFound,
#                          self.compute_images_client.delete_image,
#                          self.image['id'])

    @test.idempotent_id('4b270004-8741-4b87-9662-a2b7ead3ad8a')
    def test_get_security_group_of_alt_account(self):
        self.assertTrue(self.security_client.show_security_group,
                        self.security_group['id'])

#    def test_delete_security_group_of_alt_account_fails(self):
#        # A DELETE request for another user's security group should fail
#        self.assertRaises(lib_exc.NotFound,
#                          self.security_client.delete_security_group,
#                          self.security_group['id'])

#    def test_delete_security_group_rule_of_alt_account_fails(self):
#        # A DELETE request for another user's security group rule
#        # should fail
#        self.assertRaises(lib_exc.NotFound,
#                          self.rule_client.delete_security_group_rule,
#                          self.rule['id'])

    @test.idempotent_id('14b675e8-2c15-414c-82d1-9d1aada8feed')
    def test_set_metadata_of_alt_account_server_fails(self):
        # A set metadata for another user's server should fail
        req_metadata = {'meta1': 'tempest-server-data1',
                        'meta2': 'tempest-server-data2'}
        self.assertRaises(lib_exc.Forbidden,
                          self.client.set_server_metadata,
                          self.server['id'],
                          req_metadata)

#    def test_set_metadata_of_alt_account_image_fails(self):
#        # A set metadata for another user's image should fail
#        req_metadata = {'meta1': 'tempest-image-value1',
#                        'meta2': 'tempest-image-value2'}
#        self.assertRaises(lib_exc.Forbidden,
#                          self.compute_images_client.set_image_metadata,
#                          self.image['id'], req_metadata)

    @test.idempotent_id('ec007eeb-ab5e-4133-95a5-29c6193573e6')
    def test_get_metadata_of_alt_account_server_fails(self):
        # A get metadata for another user's server should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.client.show_server_metadata_item,
                          self.server['id'], 'meta1')

    @test.idempotent_id('0e59157a-f35a-4a03-a79a-95c15e3afe01')
    def test_get_metadata_of_alt_account_image_fails(self):
        # A get metadata for another user's image should fail
        self.assertRaises(
            lib_exc.NotFound,
            self.compute_images_client.show_image_metadata_item,
            self.image['id'], 'meta1')

    @test.idempotent_id('0c6ba418-1333-479d-9a88-833fe37562be')
    def test_delete_metadata_of_alt_account_server_fails(self):
        # A delete metadata for another user's server should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.client.delete_server_metadata_item,
                          self.server['id'], 'meta1')

#    def test_delete_metadata_of_alt_account_image_fails(self):
#        # A delete metadata for another user's image should fail
#        self.assertRaises(
#            lib_exc.NotFound,
#            self.compute_images_client.delete_image_metadata_item,
#            self.image['id'], 'meta1')

    @test.attr(type=['negative'])
    @test.idempotent_id('0980be9f-1f82-4687-891c-61f1ed2df085')
    def test_get_console_output_of_alt_account_server_fails(self):
        # A Get Console Output for another user's server should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.client.get_console_output,
                          self.server['id'], length=10)

    @test.attr(type=['negative'])
    @test.idempotent_id('9422de9d-2884-480d-8ec1-50f9812f066d')
    def test_rebuild_server_for_alt_account_fails(self):
        # A rebuild request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.rebuild_server,
                          self.server['id'], self.image_ref_alt)

    @test.attr(type=['negative'])
    @test.idempotent_id('3aa96f2c-3f11-4349-b8cb-6265717f4096')
    def test_resize_server_for_alt_account_fails(self):
        # A resize request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.resize_server,
                          self.server['id'], self.flavor_ref_alt)

    @test.attr(type=['negative'])
    @test.idempotent_id('24c79574-54cf-45f8-aec5-a5d26b2e1667')
    def test_reboot_server_for_alt_account_fails(self):
        # A reboot request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.reboot_server,
                          self.server['id'], type='HARD')

    @test.attr(type=['negative'])
    @test.idempotent_id('e60e34c2-b05d-40f4-910b-85de186f9bbc')
    def test_delete_server_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden, self.client.delete_server,
                          self.server['id'])
# EOF
