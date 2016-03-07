#!/bin/bash

# init.sh
# Check and try to install the required softwares
# Prepare the environment to execute tests

# Check the running directory vs script directory
DIRNAME="$( cd "$(dirname "$0")" ; pwd -P )"
RUNDIR=$(pwd)

if [[ $RUNDIR = /*/tools ]]; then
    cd ..
    RUNDIR=$(pwd)
    TEMPEST=$RUNDIR/tempest
elif [ -f check_openstack.sh ]; then
    TEMPEST=$RUNDIR/tempest
else
    echo "Please run this script from the top working or the tools directory"
    exit 1
fi

# Initialise and update the submodule
echo "Initializing tempest submodule..."
git submodule init

echo "Updating tempest submodule..."
git submodule update

# Update/Install packages
# Centos needs EPEL repository
if $(grep 'centos\|rhel' /etc/os-release -i -q) ; then
    if which sudo > /dev/null ; then
        sudo yum install -y epel-release
        sudo yum update
        sudo yum install -y bc libffi-devel openssl-devel python-pip python-virtualenv gcc
    else
        echo "You need to manually install these packages as root :"
        echo "yum install -y libffi-devel openssl-devel python-pip python-virtualenv gcc"
        echo "... and restart this script"
        exit 1
    fi
elif $(grep 'debian\|ubuntu' /etc/os-release -i -q) ; then
    if ! apt-cache search python-pip | grep pip ; then
        echo "You muse activate the universe repository (or whatever provides 'python-pip')"
        echo "Then run 'apt-get update' as root"
        echo "... and restart this script"
        exit 1
    fi
    
    if which sudo > /dev/null ; then
        sudo apt-get update
        sudo apt-get install -y libffi-dev libssl-dev python-dev python-virtualenv gcc
    else
        echo "You need to manually install these packages as root :"
        echo "apt-get install -y libffi-dev libssl-dev python-dev python-virtualenv gcc"
        echo "... and restart this script"
        exit 1
    fi
fi

# Start the tempest install
cd $TEMPEST

# First upgrade pip binary
if which sudo > /dev/null ; then
    sudo -H pip install --upgrade pip
else
    echo "Please run this command as root :"
    echo "pip install --upgrade pip"
    echo "... and restart this script"
    exit 1
fi

# Install the Virtual Environment if not present
if [ ! -d .venv ]; then
    python ./tools/install_venv.py
fi

# Install the Testr Repository if not present
if [ ! -d .testrepository ]; then
    .venv/bin/testr init
fi

cd ..

# Finally, copy the premade scripts to tempest working dir
mkdir $TEMPEST/tempest/api/fgcloud/
cp -al $RUNDIR/custom/test_user_isolation_* $TEMPEST/tempest/api/fgcloud/
cp -al $RUNDIR/custom/test_basic_* $TEMPEST/tempest/scenario/

## EOF
