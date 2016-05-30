#!/bin/bash

# Check the running directory vs script directory
DIRNAME="$( cd "$(dirname "$0")" ; pwd -P )"
RUNDIR=$(pwd)

if [[ $RUNDIR = /*/tools ]]; then
    cd ../tempest
elif [ -f check_openstack.sh ]; then
    cd tempest
else
    echo "Please run this script from the top working or the tools directory"
    exit 1
fi

tox -v -euuidgen
