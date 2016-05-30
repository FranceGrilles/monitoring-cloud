#!/bin/bash
source ../config/admin-creds

prefix=tempest

keystone user-list | grep $prefix | awk '{print $2}' > /tmp/tmp-users
nb_users=$(cat /tmp/tmp-users | wc -l)
keystone tenant-list | grep $prefix | awk '{print $2}' > /tmp/tmp-tenants
nb_tenants=$(cat /tmp/tmp-tenants | wc -l)
neutron router-list | grep $prefix | awk '{print $2}' > /tmp/tmp-routers
nb_routers=$(cat /tmp/tmp-routers | wc -l)
neutron subnet-list | grep $prefix | awk '{print $2}' > /tmp/tmp-subnets
nb_subnets=$(cat /tmp/tmp-subnets | wc -l)
neutron net-list | grep $prefix | awk '{print $2}' > /tmp/tmp-nets
nb_nets=$(cat /tmp/tmp-nets | wc -l)

if [[ $nb_users == "0" && $nb_tenants == "0" && $nb_routers == "0" && $nb_subnets == "0" && $nb_nets == "0" ]]; then
	echo "Nothing to delete ? Cancelling..."
	exit 1
else
	echo "Let's go..."
fi

echo "Users to delete : $nb_users"
now=$nb_users
for id in $(cat /tmp/tmp-users) ; do 
   keystone user-delete $id
   now=$((now - 1))
   echo "Done for $id, still $now / $nb_users users to do !"
done

echo "Tenants to delete : $nb_tenants"
now=$nb_tenants
for id in $(cat /tmp/tmp-tenants) ; do 
   keystone tenant-delete $id
   now=$((now - 1))
   echo "Done for $id, still $now / $nb_tenants tenants to do !"
done

echo "Routers to delete : $nb_routers"
now=$nb_routers
for id in $(cat /tmp/tmp-routers) ; do 
   neutron router-gateway-clear $id
   subnet_ids=$(neutron router-port-list $id | grep subnet_id | awk -F '"' '{ print $4; }')
   for sub_id in $subnet_ids ; do
      neutron router-interface-delete $id $sub_id
   done
   neutron router-delete $id
   now=$((now - 1))
   echo "Done for $id, still $now / $nb_routers routers to do !"
done

echo "Subnets to delete : $nb_subnets"
now=$nb_subnets
for id in $(cat /tmp/tmp-subnets) ; do 
   neutron subnet-delete $id
   now=$((now - 1))
   echo "Done for $id, still $now / $nb_subnets subnets to do !"
done

echo "Networks to delete : $nb_nets"
now=$nb_nets
for id in $(cat /tmp/tmp-nets) ; do 
   neutron net-delete $id
   now=$((now - 1))
   echo "Done for $id, still $now / $nb_nets networks to do !"
done

echo "Done !"
