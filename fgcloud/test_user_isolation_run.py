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
import testtools
import time
from oslo_log import log as logging
from tempest.api.compute import base
from tempest import config
from tempest.common.utils import data_utils
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
            skip_msg = ("%s skipped as Glance is not available" % cls.__name__)
            raise cls.skipException(skip_msg)
        if not CONF.service_available.cinder:
            skip_msg = ("%s skipped as Cinder is not available" % cls.__name__)
            raise cls.skipException(skip_msg)

    @classmethod
    def setup_credentials(cls):
        super(UserIsolationRun, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(UserIsolationRun, cls).setup_clients()
        cls.client = cls.os.servers_client
        cls.compute_images_client = cls.os.compute_images_client
        cls.image_client = cls.os.image_client
        cls.keypairs_client = cls.os.keypairs_client
        cls.security_client = cls.os.compute_security_groups_client
        cls.rule_client = cls.os.compute_security_group_rules_client
        cls.snapshots_client = cls.os.snapshots_extensions_client
        if CONF.volume_feature_enabled.api_v1:
            cls.volumes_client = cls.os.volumes_client
        else:
            cls.volumes_client = cls.os.volumes_v2_client

    @classmethod
    def resource_setup(cls):
        super(UserIsolationRun, cls).resource_setup()

        LOG.info("Starting VM_Run")
        name = data_utils.rand_name('VM_Run')
        server = cls.create_test_server(name=name, wait_until='ACTIVE')
        cls.server_run = cls.client.show_server(server['id'])['server']
        LOG.info("VM_Run started and active ")

        LOG.info("Waiting for VM_Setup to get ready...")
        while not os.path.exists(file_path):
            time.sleep(3)

        f = open(file_path)
        fileinfo = json.load(f)
        f.close()

        cls.server = fileinfo['server']
        if not CONF.compute_feature_enabled.snapshot:
            LOG.info("Snapshot skipped as instance/image snapshotting is not enabled")
        else:
            cls.server_snapshot = fileinfo['server_snapshot']
        cls.keypairname = fileinfo['keypairname']
        cls.security_group = fileinfo['security_group']
        cls.rule = fileinfo['rule']
        cls.volume1 = fileinfo['volume1']
        cls.metadata = fileinfo['metadata']
        cls.volume2 = fileinfo['volume2']
        if not CONF.volume_feature_enabled.snapshot:
            LOG.info("Snapshot skipped as volume snapshotting is not enabled")
        else:
            cls.vol_snapshot = fileinfo['vol_snapshot']
        cls.attachment = fileinfo['attachment']

        LOG.info("Running isolation tests from user B...")

    @classmethod
    def resource_cleanup(cls):
        if hasattr(cls, 'server'):
            cls.client.delete_server(cls.server_run['id'])
        os.remove(file_path)
        super(UserIsolationRun, cls).resource_cleanup()

# General
    @test.attr(type=['negative'])
    @test.idempotent_id('ebb37040-ea80-4d73-811f-7cb9a4846a7e')
    def test_get_keypair_of_alt_account_fails(self):
        self.assertRaises(lib_exc.NotFound,
                          self.keypairs_client.show_keypair,
                          self.keypairname)

    @test.attr(type=['negative'])
    @test.idempotent_id('35c4d575-423d-4b8c-ab2a-3447b9677422')
    def test_delete_keypair_of_alt_account_fails(self):
        self.assertRaises(lib_exc.NotFound,
                          self.keypairs_client.delete_keypair,
                          self.keypairname)

    @test.idempotent_id('137f2014-79a7-4dcf-8e1c-710893b12d1f')
    def test_get_security_group_of_alt_account(self):
        self.assertTrue(self.security_client.show_security_group,
                        self.security_group['id'])

# Server
    @test.idempotent_id('1fb19bb3-d40b-49e3-b6f8-04e8ca354067')
    def test_get_server_of_alt_account(self):
        self.assertTrue(self.client.show_server,
                        self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('1e66dee1-1498-4ebb-9304-b952bf4e3ee3')
    def test_update_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.update_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('5c968a59-aeae-4211-b227-adcc9ecd622c')
    def test_delete_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.delete_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('36c0b45f-cac3-4aa3-95aa-6722d697de9b')
    def test_get_server_metadata_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.list_server_metadata,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('c5011b7a-8e11-4f05-86fe-8e1b8b0ab5b1')
    def test_update_server_metadata_of_alt_account_server_fails(self):
        req_metadata = {'tempest_meta_key': 'tempest-server-data1'}
        self.assertRaises(lib_exc.Forbidden,
                          self.client.set_server_metadata,
                          self.server['id'],
                          req_metadata)

    @test.attr(type=['negative'])
    @test.idempotent_id('bc8dd9e7-86a4-4bbf-858b-6eb03c9f5655')
    def test_delete_server_metadata_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.delete_server_metadata_item,
                          self.server['id'],
                          'meta1')

    @test.attr(type=['negative'])
    @test.idempotent_id('caa72f38-63e4-41ce-bfd8-b134d22e919e')
    def test_get_server_password_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.show_password,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('6a990add-e4cc-4c99-99f7-b06c5ab88b5f')
    def test_update_server_password_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.change_password,
                          self.server['id'],
                          adminPass='newpass')

    @test.attr(type=['negative'])
    @test.idempotent_id('0d0f26c4-f69a-4e71-abe8-a342c6975f14')
    def test_get_console_output_of_alt_account_server_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.get_console_output,
                          self.server['id'],
                          length=10)

    @test.attr(type=['negative'])
    @test.idempotent_id('7aafc3bd-e664-4f69-b122-6a6e3e551188')
    def test_get_vnc_console_of_alt_account_server_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.get_vnc_console,
                          self.server['id'],
                          type='novnc')

    @test.attr(type=['negative'])
    @test.idempotent_id('3080119d-6fa1-489d-9621-f983aff725ed')
    def test_rebuild_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.rebuild_server,
                          self.server['id'],
                          self.image_ref_alt)

    @test.attr(type=['negative'])
    @test.idempotent_id('827625bb-048d-4cf3-b489-2b36594fb5f8')
    def test_resize_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.resize_server,
                          self.server['id'],
                          self.flavor_ref_alt)

    @test.attr(type=['negative'])
    @test.idempotent_id('9df2b0f5-ea2b-41ff-8401-0d1a00dc864a')
    def test_reboot_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.reboot_server,
                          self.server['id'], type='HARD')

    @test.attr(type=['negative'])
    @test.idempotent_id('65e47d5a-8bd4-406b-8d19-52c3eba6f65a')
    def test_start_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.start_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('56e11972-faac-4487-9420-031ee379319c')
    def test_stop_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.stop_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('7e921ec4-ecec-4a1b-b673-da2f9dc009cc')
    def test_lock_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.lock_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('68cfdda6-0475-4734-909d-b2fe21987347')
    def test_unlock_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.unlock_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('41b5975f-e140-4cc9-83af-a83b8b6cf278')
    def test_pause_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.pause_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('0a1c4f53-fa8a-4ae9-b5ab-e55e539024d1')
    def test_unpause_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.unpause_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('5af863a1-f10c-4a3a-a3de-2bf3506247f5')
    def test_suspend_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.suspend_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('4b93e4b9-b33f-4ff1-8cd0-5f1efe20624b')
    def test_resume_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.resume_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('1aea9960-897f-4273-ae69-bbd9bc45c359')
    def test_shelve_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.shelve_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('67e59d60-ccfc-443c-ac9b-9bcaf35044b6')
    def test_unshelve_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.unshelve_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('0309c7ef-27af-4934-9cc0-66b37085b227')
    def test_shelve_offload_server_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.client.shelve_offload_server,
                          self.server['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('088de95a-825c-4773-bf7d-26d9d830f741')
    def test_create_server_snapshot_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.compute_images_client.create_image,
                          self.server['id'], name='test_snapshot')

# Image
    @test.idempotent_id('383c3525-48e9-47b1-9533-1eed490402de')
    def test_get_image_of_alt_account(self):
        self.assertTrue(self.compute_images_client.show_image,
                        CONF.compute.image_ref)

    @test.attr(type=['negative'])
    @test.idempotent_id('272698ef-994a-4e94-b187-9d65f2ab731b')
    def test_update_image_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.image_client.update_image,
                          CONF.compute.image_ref)

    @test.attr(type=['negative'])
    @test.idempotent_id('794e34e0-3752-4516-8c10-09923bf61e01')
    def test_delete_image_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.image_client.delete_image,
                          CONF.compute.image_ref)

    @test.idempotent_id('197f8b8e-d41d-4060-9266-f60b2e179a26')
    def test_get_image_metadata_of_alt_account(self):
        self.assertTrue(self.compute_images_client.list_image_metadata,
                        CONF.compute.image_ref)

    @test.idempotent_id('537a378c-1aab-4eba-b872-809f7510431f')
    @testtools.skipUnless(CONF.compute_feature_enabled.snapshot,
                          'Instance/image snapshotting is not available.')
    def test_get_server_snapshot_of_alt_account(self):
        self.assertTrue(self.compute_images_client.show_image,
                        self.server_snapshot['id'])

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.compute_feature_enabled.snapshot,
                          'Instance/image snapshotting is not available.')
    @test.idempotent_id('e8e5ee2b-904d-4c9d-9765-ae433eecbf6b')
    def test_update_server_snapshot_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.image_client.update_image,
                          self.server_snapshot['id'])

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.compute_feature_enabled.snapshot,
                          'Instance/image snapshotting is not available.')
    @test.idempotent_id('bf89b4ca-17a9-4474-b3ec-ff5549bde157')
    def test_delete_server_snapshot_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.image_client.delete_image,
                          self.server_snapshot['id'])

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.compute_feature_enabled.snapshot,
                          'Instance/image snapshotting is not available.')
    @test.idempotent_id('3a682f31-9882-411c-91c5-4f4303eb6194')
    def test_get_server_snapshot_metadata_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.compute_images_client.list_image_metadata,
                          self.server_snapshot['id'])

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.compute_feature_enabled.snapshot,
                          'Instance/image snapshotting is not available.')
    @test.idempotent_id('3185f333-6de3-4c0a-9838-62e67ea39e5e')
    def test_update_server_snapshot_metadata_of_alt_account_fails(self):
        metadata = {'key1': 'alt1', 'key2': 'value2'}
        self.assertRaises(lib_exc.Forbidden,
                          self.compute_images_client.update_image_metadata,
                          self.server_snapshot['id'], metadata)

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.compute_feature_enabled.snapshot,
                          'Instance/image snapshotting is not available.')
    @test.idempotent_id('898766e0-9774-42a3-ac7f-b9cf96e03aae')
    def test_delete_server_snapshot_metadata_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.compute_images_client.delete_image_metadata_item,
                          self.server_snapshot['id'],
                          'meta1')

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.compute_feature_enabled.snapshot,
                          'Instance/image snapshotting is not available.')
    @test.idempotent_id('795eb920-fd89-4c87-abce-fe760bd32a51')
    def test_create_server_from_snapshot_of_alt_account_fails(self):
        name = data_utils.rand_name('VM_From_Snapshot')
        self.assertRaises(lib_exc.ServerFault,
                          self.client.create_server,
                          name=name,
                          imageRef=self.server_snapshot['id'],
                          flavorRef=CONF.compute.flavor_ref)

# Volume
    @test.idempotent_id('ee2c468b-1cf2-4d70-abe4-6d13f8d5ad8a')
    def test_get_volume_of_alt_account(self):
        self.assertTrue(self.volumes_client.show_volume,
                        self.volume1['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('3a7f0ebf-b36d-4899-b607-bcc5e998ed72')
    def test_update_volume_of_alt_account_fails(self):
        try:
            self.volumes_client.update_volume(self.volume1['id'])
        except lib_exc.Forbidden:
            pass
        except lib_exc.NotFound:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @test.idempotent_id('0bce9bd7-4032-4c81-b277-093bb9058219')
    def test_delete_volume_of_alt_account_fails(self):
        try:
            self.volumes_client.delete_volume(self.volume1['id'])
        except lib_exc.Forbidden:
            pass
        except lib_exc.NotFound:
            pass
        except:
            raise

    @test.idempotent_id('49c06e08-d56e-48c6-846f-b9256370760b')
    def test_get_volume_metadata_of_alt_account(self):
        self.assertTrue(self.volumes_client.show_volume_metadata,
                        self.volume1['id'])

    @test.attr(type=['negative'])
    @test.idempotent_id('d279a2c0-f554-4ae9-9a39-2a5caf9fced3')
    def test_update_volume_metadata_of_alt_account_fails(self):
        metadata = {'new_meta': data_utils.rand_name('new_metadata')}
        try:
            self.volumes_client.update_volume_metadata(self.volume1['id'],
                                                       metadata)
        except lib_exc.Forbidden:
            pass
        except lib_exc.NotFound:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @test.idempotent_id('b4a11b21-72c6-4450-985c-6ea9bd0e6d36')
    def test_delete_volume_metadata_of_alt_account_fails(self):
        try:
            self.volumes_client.delete_volume_metadata_item(self.volume1['id'],
                                                            'vol_metadata')
        except lib_exc.Forbidden:
            pass
        except lib_exc.NotFound:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @test.idempotent_id('1c48d877-6f4b-480e-ab18-5fe26418bc0a')
    def test_attach_volume_of_alt_account_fails(self):
        try:
            self.client.attach_volume(self.server_run['id'],
                                      volumeId=self.volume1['id'])
        except lib_exc.NotFound:
            pass
        except lib_exc.Forbidden:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @test.idempotent_id('2074a6b1-5d08-4724-bfc7-61b6247a017e')
    def test_detach_volume_of_alt_account_fails(self):
        try:
            self.client.detach_volume(self.server['id'], self.volume2['id'])
        except lib_exc.Forbidden:
            pass
        except lib_exc.NotFound:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @test.idempotent_id('46e0198f-52e1-410f-8edc-a287b189d7b7')
    def test_update_volume_attachment_of_alt_account_fails(self):
        try:
            self.client.update_attached_volume(self.server['id'],
                                        attachment_id=self.attachment['id'],
                                        volumeId=self.volume1['id'])
        except lib_exc.Forbidden:
            pass
        except lib_exc.NotFound:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @test.idempotent_id('f9be1ab4-0975-4b6b-ae36-da4e7a576b24')
    def test_extend_volume_of_alt_account_fails(self):
        extend_size = int(self.volume1['size']) + 1
        try:
            self.volumes_client.extend_volume(self.volume1['id'],
                                              new_size=extend_size)
        except lib_exc.Forbidden:
            pass
        except lib_exc.NotFound:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.volume_feature_enabled.snapshot,
                          'Volume snapshotting is not available.')
    @test.idempotent_id('09cfd067-831a-47fc-ac07-13e05290cf30')
    def test_create_volume_snapshot_of_alt_account_fails(self):
        try:
            self.snapshots_client.create_snapshot(self.volume1['id'])
        except lib_exc.NotFound:
            pass
        except lib_exc.Forbidden:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.volume_feature_enabled.snapshot,
                          'Volume snapshotting is not available.')
    @test.idempotent_id('2cad9a8f-cc65-429c-a7d4-908bd86358f1')
    def test_get_volume_snapshot_of_alt_account_fails(self):
        try:
            self.snapshots_client.show_snapshot(self.vol_snapshot['id'])
        except lib_exc.NotFound:
            pass
        except lib_exc.Forbidden:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @test.idempotent_id('9a9274a8-f385-4c00-b7f9-405e13d8dd74')
    @testtools.skipUnless(CONF.volume_feature_enabled.snapshot,
                          'Volume snapshotting is not available.')
    def test_update_volume_snapshot_of_alt_account_fails(self):
        try:
            self.image_client.update_image(self.vol_snapshot['id'])
        except lib_exc.NotFound:
            pass
        except lib_exc.Forbidden:
            pass
        except:
            raise

    @test.attr(type=['negative'])
    @testtools.skipUnless(CONF.volume_feature_enabled.snapshot,
                          'Volume snapshotting is not available.')
    @test.idempotent_id('e4fb10e9-a017-4c02-8299-bc361cf04828')
    def test_delete_volume_snapshot_of_alt_account_fails(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.snapshots_client.delete_snapshot,
                          self.vol_snapshot['id'])

# EOF
