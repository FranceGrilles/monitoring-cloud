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
from tempest.api.compute import base
from tempest import config
from tempest.lib import exceptions as lib_exc
from tempest import test

CONF = config.CONF
LOG = logging.getLogger(__name__)
file_path = "/tmp/tempest_" + CONF.compute.image_ref


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

        LOG.info("Waiting for VM to get ready...")
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

        LOG.info("Running isolation tests from user B...")

    @classmethod
    def resource_cleanup(cls):
        os.remove(file_path)
        super(UserIsolationRun, cls).resource_cleanup()

    @test.idempotent_id('1fb19bb3-d40b-49e3-b6f8-04e8ca354067')
    def test_get_server_for_alt_account(self):
        self.assertTrue(self.client.show_server, self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('1e66dee1-1498-4ebb-9304-b952bf4e3ee3')
    def test_update_server_for_alt_account_fails(self):
        # An update server request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.update_server,
                          self.server['id'], name='tempest_test_rename')

    @test.idempotent_id('b293feda-861a-4d16-9a0d-6f2341a19abe')
    def test_list_server_addresses_for_alt_account(self):
        self.assertTrue(self.client.list_addresses, self.server['id'])

    @test.idempotent_id('19947773-5c36-49d1-97f1-069308215415')
    def test_list_server_addresses_by_network_for_alt_account(self):
        server_id = self.server['id']
        self.assertTrue(self.client.list_addresses_by_network, server_id)

    @test.attr(type=['negative'])
    @test.idempotent_id('6a990add-e4cc-4c99-99f7-b06c5ab88b5f')
    def test_change_password_for_alt_account_fails(self):
        # A change password request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.change_password,
                          self.server['id'], adminPass='newpass')

    @test.attr(type=['negative'])
    @test.idempotent_id('088de95a-825c-4773-bf7d-26d9d830f741')
    def test_create_image_for_alt_account_fails(self):
        # A create image request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.compute_images_client.create_image,
                          self.server['id'], name='testImage')

    @test.attr(type=['negative'])
    @test.idempotent_id('ebb37040-ea80-4d73-811f-7cb9a4846a7e')
    def test_get_keypair_of_alt_account_fails(self):
        # A GET request for another user's keypair should fail
        self.assertRaises(lib_exc.NotFound,
                          self.keypairs_client.show_keypair,
                          self.keypairname)

    @test.attr(type=['negative'])
    @test.idempotent_id('35c4d575-423d-4b8c-ab2a-3447b9677422')
    def test_delete_keypair_of_alt_account_fails(self):
        # A DELETE request for another user's keypair should fail
        self.assertRaises(lib_exc.NotFound,
                          self.keypairs_client.delete_keypair,
                          self.keypairname)

    @test.idempotent_id('383c3525-48e9-47b1-9533-1eed490402de')
    def test_get_image_for_alt_account(self):
        self.assertTrue(self.compute_images_client.show_image,
                        self.image['id'])

    @test.idempotent_id('137f2014-79a7-4dcf-8e1c-710893b12d1f')
    def test_get_security_group_of_alt_account(self):
        self.assertTrue(self.security_client.show_security_group,
                        self.security_group['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('c5011b7a-8e11-4f05-86fe-8e1b8b0ab5b1')
    def test_set_metadata_of_alt_account_server_fails(self):
        # A set metadata for another user's server should fail
        req_metadata = {'meta1': 'tempest-server-data1',
                        'meta2': 'tempest-server-data2'}
        self.assertRaises(lib_exc.Forbidden,
                          self.client.set_server_metadata,
                          self.server['id'],
                          req_metadata)

    @test.attr(type=['negative'])
    @test.idempotent_id('36c0b45f-cac3-4aa3-95aa-6722d697de9b')
    def test_get_metadata_of_alt_account_server_fails(self):
        # A get metadata for another user's server should fail
        try:
            self.client.show_server_metadata_item
        except lib_exc.Forbidden:
            self.fail('Forbidden')
        except lib_exc.NotFound:
            self.fail('NotFound')

#        self.assertRaises(lib_exc.Forbidden,
#                          self.client.show_server_metadata_item,
#                          self.server['id'], 'meta1')
#        self.assertRaises(lib_exc.NotFound,
#                          self.client.show_server_metadata_item,
#                          self.server['id'], 'meta1')

    @test.attr(type=['negative'])
    @test.idempotent_id('197f8b8e-d41d-4060-9266-f60b2e179a26')
    def test_get_metadata_of_alt_account_image_fails(self):
        # A get metadata for another user's image should fail
        self.assertRaises(
            lib_exc.NotFound,
            self.compute_images_client.show_image_metadata_item,
            self.image['id'], 'meta1')

    @test.attr(type=['negative'])
    @test.idempotent_id('bc8dd9e7-86a4-4bbf-858b-6eb03c9f5655')
    def test_delete_metadata_of_alt_account_server_fails(self):
        # A delete metadata for another user's server should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.client.delete_server_metadata_item,
                          self.server['id'], 'meta1')

    @test.attr(type=['negative'])
    @test.idempotent_id('edb92ce6-b116-472f-9134-335e9195afb6')
    def test_delete_metadata_of_alt_account_image_fails(self):
        # A delete metadata for another user's image should fail
        self.assertRaises(
            lib_exc.NotFound,
            self.compute_images_client.delete_image_metadata_item,
            self.image['id'], 'meta1')

    @test.attr(type=['negative'])
    @test.idempotent_id('0d0f26c4-f69a-4e71-abe8-a342c6975f14')
    def test_get_console_output_of_alt_account_server_fails(self):
        # A Get Console Output for another user's server should fail
        self.assertRaises(lib_exc.Forbidden,
                          self.client.get_console_output,
                          self.server['id'], length=10)

    @test.attr(type=['negative'])
    @test.idempotent_id('3080119d-6fa1-489d-9621-f983aff725ed')
    def test_rebuild_server_for_alt_account_fails(self):
        # A rebuild request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.rebuild_server,
                          self.server['id'], self.image_ref_alt)

    @test.attr(type=['negative'])
    @test.idempotent_id('827625bb-048d-4cf3-b489-2b36594fb5f8')
    def test_resize_server_for_alt_account_fails(self):
        # A resize request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.resize_server,
                          self.server['id'], self.flavor_ref_alt)

    @test.attr(type=['negative'])
    @test.idempotent_id('9df2b0f5-ea2b-41ff-8401-0d1a00dc864a')
    def test_reboot_server_for_alt_account_fails(self):
        # A reboot request for another user's server should fail
        self.assertRaises(lib_exc.Forbidden, self.client.reboot_server,
                          self.server['id'], type='HARD')

    @test.attr(type=['negative'])
    @test.idempotent_id('5c968a59-aeae-4211-b227-adcc9ecd622c')
    def test_delete_server_for_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden, self.client.delete_server,
                          self.server['id'])
# EOF
