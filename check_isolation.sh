#!/bin/bash

# Copyright 2015 France-Grilles - IDGC - CNRS
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
#
##############################################################################
# Run an isolation test between 2 users in the same tenant
##############################################################################

# Functions

usage () {
    echo "Usage: $0 [OPTION] ..."
    echo "Run an isolation test between 2 users in the same tenant"
    echo "Use check_openstack.sh to filter output"
    echo ""
    echo "  -a <path_to_file>   Use a custom tempest.conf file location for user_1"
    echo "  -b <path_to_file>   Use a custom tempest.conf file location for user_2"
    echo "  -h                  Print this help message"
    echo ""
    echo "Exemple : $0 -a config/tempest-1.conf -b config/tempest-2.conf"
    echo ""
    echo "No test was run !|time=0, nb_test=0, nb_tests_ok=0, nb_tests_ko=0, nb_skipped=0"
    echo "value : $1"
    exit 2
}

runMain () {
    {
    echo "Lauching a VM with user A..."
    ./check_openstack.sh -c $CONF_FILE_A -- tempest.api.compute.test_api_compute_user_isolation_setup 2>&1 > /dev/null
    } &

    echo "Waiting for VM to get ready..."
    sleep 20

    {
    echo "Running isolation tests from user B..."
    ./check_openstack.sh -c $CONF_FILE_B -- tempest.api.compute.test_api_compute_user_isolation_run
    } &

    wait
}

# No argument given
if [ $# -eq 0 ] ; then
    usage
fi

# Validate options
if ! OPTIONS=$(getopt -o a:b:h "$@") ; then
    usage
fi

while [ $# -gt 0 ]; do
    case "$1" in
        -a)
            CONF_FILE_A=$2
            shift 2
            ;;

        -b)
            CONF_FILE_B=$2
            shift 2
            ;;

        -h)
            usage
            ;;

        *)
            echo "Incorrect input : $1"
            usage
            ;;
    esac
done

runMain

# EOF
