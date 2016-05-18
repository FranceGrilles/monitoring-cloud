#!/bin/bash

EXT_NET_NAME=ext-net
# Max 9 users
NB_USERS_TO_CREATE=6

load_admin_creds() {
    source ../config/admin-creds
}

RAND=$(tr -dc A-Za-z0-9_ < /dev/urandom | head -c 7 | xargs)
TMP_FILE=/tmp/tempest_tmp_$RAND
LOG_FILE=/tmp/tempest_log_$RAND

echo "# Generated users for use with tempest API" > $TMP_FILE

for i in $(seq 1 $NB_USERS_TO_CREATE); do
	echo "========================= User $i =========================" 2>&1 | tee -a $LOG_FILE
	load_admin_creds
	genpass=$(tr -dc A-Za-z0-9_ < /dev/urandom | head -c 16 | xargs)
	keystone tenant-create --name tempest_tenant_$i --description "Tempest tenant $i" 2>&1 | tee -a $LOG_FILE
	keystone user-create --name tempest_user_$i --pass $genpass --tenant tempest_tenant_$i 2>&1 | tee -a $LOG_FILE

	export OS_TENANT_NAME=tempest_tenant_$i
	export OS_USERNAME=tempest_user_$i
	export OS_PASSWORD=$genpass

	neutron net-create tempest_net_$i 2>&1 | tee -a $LOG_FILE
	neutron subnet-create tempest_net_$i --name tempest_subnet_$i --gateway "192.168.24"$i".1" "192.168.24"$i".0/24" 2>&1 | tee -a $LOG_FILE
	neutron router-create tempest_router_$i 2>&1 | tee -a $LOG_FILE
	neutron router-interface-add tempest_router_$i tempest_subnet_$i 2>&1 | tee -a $LOG_FILE
	neutron router-gateway-set tempest_router_$i $EXT_NET_NAME 2>&1 | tee -a $LOG_FILE

	echo -e "\n# Test user $i" >> $TMP_FILE
	echo "- username: 'tempest_user_$i'" >> $TMP_FILE
	echo "  tenant_name: 'tempest_tenant_$i'" >> $TMP_FILE
	echo "  password: '$genpass'" >> $TMP_FILE
	echo "  resources:" >> $TMP_FILE
	echo "    network: 'tempest_net_$i'" >> $TMP_FILE

done
echo -e "\n\nLOG_FILE for job $RAND is here : $LOG_FILE" 
echo -e "\nCopy the file $TMP_FILE to accounts.yaml and use it for tempest"
echo -e "File dump :\n---start---"
cat $TMP_FILE
echo -e "\n---end---"

cp -f $TMP_FILE ../config/accounts.yaml
