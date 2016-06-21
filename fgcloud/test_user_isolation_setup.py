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
from tempest.common import waiters
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
            skip_msg = ("%s skipped as Glance is not available" % cls.__name__)
            raise cls.skipException(skip_msg)
        if not CONF.service_available.cinder:
            skip_msg = ("%s skipped as Cinder is not available" % cls.__name__)
            raise cls.skipException(skip_msg)
        if not CONF.compute_feature_enabled.snapshot:
            skip_msg = ("%s skipped as instance snapshotting is not supported"
                        % cls.__name__)
            raise cls.skipException(skip_msg)

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
        cls.image_client = cls.os.image_client
        cls.keypairs_client = cls.os.keypairs_client
        cls.security_client = cls.os.compute_security_groups_client
        cls.rule_client = cls.os.compute_security_group_rules_client
        cls.volumes_client = cls.os.volumes_client
        cls.snapshots_client = cls.os.snapshots_extensions_client

    @classmethod
    def resource_setup(cls):
        super(UserIsolationSetup, cls).resource_setup()

        # Prepare an array to store information
        fileinfo = {}
        if os.path.exists(file_path):
            LOG.info("/!\\ deleting previous file /!\\")
            os.remove(file_path)

        # Create a server
        LOG.info("setting up server...")
        name = data_utils.rand_name('VM_Setup')
        server = cls.create_test_server(name=name, wait_until='ACTIVE')
        cls.server = cls.client.show_server(server['id'])['server']
        fileinfo['server'] = cls.server
        LOG.info("VM_Setup created and active")


        # Create an image
        name = data_utils.rand_name('image')
        body = cls.compute_images_client.create_image(cls.server['id'],
                                                      name=name)
        image_id = data_utils.parse_image_id(body.response['location'])
        waiters.wait_for_image_status(cls.compute_images_client,
                                      image_id, 'ACTIVE')
        cls.image = cls.compute_images_client.show_image(image_id)['image']
        fileinfo['image'] = cls.image
        LOG.info("image created and active")

        # Create a keypair
        cls.keypairname = data_utils.rand_name('keypair')
        cls.keypairs_client.create_keypair(name=cls.keypairname)
        fileinfo['keypairname'] = cls.keypairname
        LOG.info("keypair created")

        # Create a security group
        name = data_utils.rand_name('security')
        description = data_utils.rand_name('description')
        cls.security_group = cls.security_client.create_security_group(
            name=name, description=description)['security_group']
        fileinfo['security_group'] = cls.security_group
        LOG.info("security group created")

        # Create a security group rule
        cls.rule = cls.rule_client.create_security_group_rule(
            parent_group_id=cls.security_group['id'], ip_protocol='tcp',
            from_port=22, to_port=22)['security_group_rule']
        fileinfo['rule'] = cls.rule
        LOG.info("security rule created")

        # Create two volumes
        name = data_utils.rand_name('volume1')
        cls.metadata = {'vol_metadata': data_utils.rand_name('vol_metadata')}
        cls.volume1 = cls.volumes_client.create_volume(
            size=1, display_name=name, metadata=cls.metadata)['volume']
        name = data_utils.rand_name('volume2')
        cls.volume2 = cls.volumes_client.create_volume(
            size=1, display_name=name)['volume']
        waiters.wait_for_volume_status(cls.volumes_client,
                                       cls.volume1['id'], 'available')
        waiters.wait_for_volume_status(cls.volumes_client,
                                       cls.volume2['id'], 'available')
        fileinfo['volume1'] = cls.volume1
        fileinfo['metadata'] = cls.metadata
        fileinfo['volume2'] = cls.volume2
        LOG.info("volumes created")

        # Create a snapshot from volume1
        name = data_utils.rand_name('snapshot')
        cls.snapshot = cls.snapshots_client.create_snapshot(
            volume_id=cls.volume1['id'],
            display_name=name)['snapshot']
        waiters.wait_for_snapshot_status(cls.snapshots_client,
                                         cls.snapshot['id'],
                                         'available')
        fileinfo['snapshot'] = cls.snapshot
        LOG.info("snapshot created")

        # Attach volume2 to the server
        cls.attachment = cls.servers_client.attach_volume(
            cls.server['id'],
            volumeId=cls.volume2['id'])['volumeAttachment']
        waiters.wait_for_volume_status(cls.volumes_client,
                                       cls.volume2['id'], 'in-use')
        fileinfo['attachment'] = cls.attachment
        LOG.info("volume attached to server")

        # Save array information to file
        f = open(file_path, 'w')
        json.dump(fileinfo, f)
        f.close()
        LOG.info("file created with ids, waiting...")

    @classmethod
    def resource_cleanup(cls):
        if hasattr(cls, 'attachment'):
            cls.client.detach_volume(cls.server['id'], cls.volume2['id'])
            waiters.wait_for_volume_status(cls.volumes_client,
                                           cls.volume2['id'], 'available')
        if hasattr(cls, 'snapshot'):
            cls.snapshots_client.delete_snapshot(cls.snapshot['id'])
            cls.snapshots_client.wait_for_resource_deletion(cls.snapshot['id'])
        if hasattr(cls, 'volume1'):
            cls.volumes_client.delete_volume(cls.volume1['id'])
            cls.volumes_client.wait_for_resource_deletion(cls.volume1['id'])
        if hasattr(cls, 'volume2'):
            cls.volumes_client.delete_volume(cls.volume2['id'])
            cls.volumes_client.wait_for_resource_deletion(cls.volume2['id'])
        if hasattr(cls, 'image'):
            cls.compute_images_client.delete_image(cls.image['id'])
        if hasattr(cls, 'keypairname'):
            cls.keypairs_client.delete_keypair(cls.keypairname)
        if hasattr(cls, 'security_group'):
            cls.security_client.delete_security_group(cls.security_group['id'])
        if hasattr(cls, 'server'):
            cls.client.delete_server(cls.server['id'])
        if os.path.exists(file_path):
            os.remove(file_path)
        super(UserIsolationSetup, cls).resource_cleanup()

    @test.idempotent_id('30d8f7d5-84cc-47e1-9ccd-e694ab86b685')
    def test_wait_for_test_to_terminate(self):
        while os.path.exists(file_path):
            time.sleep(3)

# EOF
