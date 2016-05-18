#!/bin/bash
source ../config/admin-creds

keystone user-list | grep tempest | awk '{print $2}' > /tmp/tmp-users
nb_users=$(cat /tmp/tmp-users | wc -l)
keystone tenant-list | grep tempest | awk '{print $2}' > /tmp/tmp-tenants
nb_tenants=$(cat /tmp/tmp-tenants | wc -l)
neutron router-list | grep tempest | awk '{print $2}' > /tmp/tmp-routers
nb_routers=$(cat /tmp/tmp-routers | wc -l)
neutron subnet-list | grep tempest | awk '{print $2}' > /tmp/tmp-subnets
nb_subnets=$(cat /tmp/tmp-subnets | wc -l)
neutron net-list | grep tempest | awk '{print $2}' > /tmp/tmp-nets
nb_nets=$(cat /tmp/tmp-nets | wc -l)

echo "There are :"
echo "- $nb_users users"
echo "- $nb_tenants tenants"
echo "- $nb_routers routers"
echo "- $nb_subnets subnets"
echo "- $nb_nets networks"
echo "that contains \"tempest\" in their names"
