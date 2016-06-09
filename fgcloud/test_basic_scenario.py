# Copyright 2013 NEC Corporation
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
import time
from oslo_log import log as logging
from tempest.common import custom_matchers
from tempest.common import waiters
from tempest import config
from tempest import exceptions
from tempest.scenario import manager
from tempest import test

CONF = config.CONF
LOG = logging.getLogger(__name__)


class TestBasicScenario(manager.ScenarioTest):

    """This is a basic scenario test.

    This test works:
    * across multiple components
    * as a regular user
    * check command outputs

    Steps:
    1. Use existing image ref
    2. Create keypair
    3. Boot instance with keypair and get list of instances
    4. Create volume and show list of volumes
    5. Attach volume to instance and get list of volumes
    6. Add IP to instance
    7. Create and add security group to instance
    8. Check SSH connection to instance
    9. Write a timestamp onto the attached volume
    10. Reboot instance
    11. Check SSH connection to instance after reboot
    12. Read/Compare the timestamp onto the attached volume

    """

    def _wait_for_server_status(self, server, status):
        server_id = server['id']
        # Raise on error defaults to True, which is consistent with the
        # original function from scenario tests here
        waiters.wait_for_server_status(self.servers_client,
                                       server_id, status)

    def nova_list(self):
        servers = self.servers_client.list_servers()
        # The list servers in the compute client is inconsistent...
        return servers['servers']

    def nova_show(self, server):
        got_server = (self.servers_client.show_server(server['id'])
                      ['server'])
        excluded_keys = ['OS-EXT-AZ:availability_zone']
        # Exclude these keys because of LP:#1486475
        excluded_keys.extend(['OS-EXT-STS:power_state', 'updated'])
        self.assertThat(
            server, custom_matchers.MatchesDictExceptForKeys(
                got_server, excluded_keys=excluded_keys))

    def cinder_create(self):
        return self.create_volume()

    def cinder_list(self):
        return self.volumes_client.list_volumes()['volumes']

    def cinder_show(self, volume):
        got_volume = self.volumes_client.show_volume(volume['id'])['volume']
        self.assertEqual(volume, got_volume)

    def nova_reboot(self, server):
        self.servers_client.reboot_server(server['id'], type='SOFT')
        self._wait_for_server_status(server, 'ACTIVE')

    def check_partitions(self):
        # NOTE(andreaf) The device name may be different on different guest OS
        partitions = self.linux_client.get_partitions()
        self.assertEqual(1, partitions.count(CONF.compute.volume_device_name))

    def create_and_add_security_group_to_server(self, server):
        secgroup = self._create_security_group()
        self.servers_client.add_security_group(server['id'],
                                               name=secgroup['name'])
        self.addCleanup(self.servers_client.remove_security_group,
                        server['id'], name=secgroup['name'])

        def wait_for_secgroup_add():
            body = (self.servers_client.show_server(server['id'])
                    ['server'])
            return {'name': secgroup['name']} in body['security_groups']

        if not test.call_until_true(wait_for_secgroup_add,
                                    CONF.compute.build_timeout,
                                    CONF.compute.build_interval):
            msg = ('Timed out waiting for adding security group %s to server '
                   '%s' % (secgroup['id'], server['id']))
            raise exceptions.TimeoutException(msg)
        return secgroup['name']

    @test.idempotent_id('53f75314-eed0-4db6-8f43-b21883d3941f')
    @test.services('compute', 'volume', 'image', 'network')
    def test_basic_scenario(self):

        # Create an image from local files (see conf.scenario.*_img_file)
        # image = self.glance_image_create()
        # -or-
        # Use existing image (faster)
        image = CONF.compute.image_ref
        LOG.info('Use existing image ref : %s' % image)

        # Create keypair for auth
        LOG.info('Creating keypair...')
        keypair = self.create_keypair()
        LOG.info('Keypair created : %s (%s)', keypair['name'],
                 keypair['fingerprint'])

        # Create and boot server
        LOG.info('Creating server...')
        server = self.create_server(image_id=image,
                                    key_name=keypair['name'],
                                    wait_until='ACTIVE')
        servers = self.nova_list()
        self.assertIn(server['id'], [x['id'] for x in servers])
        LOG.info('Server created : %s', server['name'])

        #LOG.info(self.nova_show(server))

        # Create a new volume
        LOG.info('Creating volume...')
        volume = self.cinder_create()
        volumes = self.cinder_list()
        self.assertIn(volume['id'], [x['id'] for x in volumes])
        if 'display_name' in volume:
            volume_name = volume['display_name']
        else:
            volume_name = volume['name']
        LOG.info('Volume created : %s', volume_name)

        #LOG.info(self.cinder_show(volume))

        # Attach volume to server
        LOG.info('Attaching volume to instance...')
        volume = self.nova_volume_attach(server, volume)
        self.addCleanup(self.nova_volume_detach, server, volume)

        #LOG.info(self.cinder_show(volume))

        # Create and associate a floating_ip to the server
        # We need to specify the pool_name as we may have multiple networks
        LOG.info('Creating Floating IP...')
        fip_net = CONF.network.floating_network_name
        floating_ip = self.create_floating_ip(server, pool_name=fip_net)
        LOG.info('Floating IP created : %s (%s)', floating_ip['id'],
                 floating_ip['ip'])

        LOG.info('Creating Security Group...')
        sec_grp_name = self.create_and_add_security_group_to_server(server)
        LOG.info('Security Group created : %s' % sec_grp_name)

        # check that we can PING and SSH to the server
        LOG.info('Checking connectivity...')
        ping_result = self.ping_ip_address(ip_address=floating_ip['ip'])
        self.linux_client = self.get_remote_client(
            floating_ip['ip'], private_key=keypair['private_key'])
        LOG.info('Ping to Floating IP : %s' % ping_result)

        # Create a timestamp on the volume
        vdev_name = CONF.compute.volume_device_name
        timestamp = self.create_timestamp(floating_ip['ip'],
                                          dev_name=vdev_name,
                                          private_key=keypair['private_key'])
        LOG.info('Timestamp created on /dev/%s', vdev_name)

        # Reboot server
        LOG.info('Server Rebooting...')
        self.nova_reboot(server)

        # check that we can SSH to the server after reboot
        self.linux_client = self.get_remote_client(
            floating_ip['ip'], private_key=keypair['private_key'])

        #self.check_partitions()

        # Check timestamp on volume after reboot
        LOG.info('Checking timestamp...')
        timestamp2 = self.get_timestamp(floating_ip['ip'],
                                        dev_name=vdev_name,
                                        private_key=keypair['private_key'])
        self.assertEqual(timestamp, timestamp2)
        LOG.info('End of tests, cleaning...')
