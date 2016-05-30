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

from oslo_log import log as logging
from tempest import config
from tempest.scenario import manager
from tempest import test
import testtools
import time
CONF = config.CONF
LOG = logging.getLogger(__name__)


class TestBasicValues(manager.ScenarioTest):

    """This is a basic values test.

    This test works:
    * as a regular user

    Steps:
    1. Checks if the result/errors are displayed

    """

    @test.idempotent_id('8260e8f5-0f3d-4c72-80b8-14442b43de50')
    def test_basic_values_true(self):
        time.sleep(2)
        LOG.info("info message in OK")
        LOG.warn("warn message in OK")
        LOG.critical("crit message in OK")
        self.assertEqual(4, 2 * 2)

    @test.idempotent_id('a5421964-eedc-4304-9fd0-f25c8f0ec667')
    def test_basic_values_false_warn(self):
        LOG.warn("warn message in FAILED 1")
        self.assertEqual(5, 2 * 2)

    @test.idempotent_id('2a50691f-91cd-45d2-bbef-4c2ab8b8536f')
    def test_basic_values_false_crit(self):
        LOG.critical("crit message in FAILED 2")
        self.assertEqual(6, 2 * 2)

    @test.idempotent_id('3f303565-8f22-404e-ade9-6661529440b2')
    @testtools.skipIf(1, 'Skipped Test')
    def test_basic_values_skipped(self):
        LOG.info("skipped test")
