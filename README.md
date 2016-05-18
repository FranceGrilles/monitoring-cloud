# monitoring-cloud
Collection of scripts to monitor OpenStack IaaS Cloud via Tempest API.

tempest is loaded as a git submodule from https://github.com/openstack/tempest/

## Goals
Use tempest to monitor the stack and present the results to Nagios/Icinga

With access to the API services fgcloud-scripts will try to :

* add/upload custom image (small one like cirros or tinylinux)
* create a tiny node with that image and a custom SSH-key
* create/attach a public IP address
* create/attach a permanent storage
* login using SSH-key
  * mount permanent storage
  * check writing and reading from the storage
  * unmount, reboot, recheck
* cleanup

-> Done in the tempest.api.fgcloud.test_basic_scenario module

## Usage
```
Usage: ./check_openstack.sh [OPTION] ...
Run Tempest test suite and filter output for monitoring by Nagios/Icinga
Output list of tests, failure traces, and performance data

  -c, --config <path_to_file>     Use a custom tempest.conf file location (default : config/tempest.conf)
  -e, --regex '^tempest\.regex'   Launch tests according to the regex (better in quotes)
  -h, --help                      Print this usage message
  -t, --timeout <time_in_sec>     Raise a WARNING if the test(s) run longer (default : 120)
  -u, --update                    Update the virtual environment (does not run any test)
  -- <single.test.to.run>         After any other options add a double dash following a test.name.to.run

Exemple : ./check_openstack.sh -t 90 -- tempest.api.fgcloud.test_basic_scenario
Exemple : ./check_openstack.sh -e '(^tempest\.api\.fgcloud\.test_basic_(scenario|values))'
```
## Setup / Installation

First `git clone --recursive https://github.com/FranceGrilles/monitoring-cloud.git`

Check the content of the 'config' directory and edit/rename/copy any of these files to suits your environment :
* `admin-creds` : store the admin user information (only used by the tools/scripts to create/list/delete users)
* `accounts.yaml` : used to store the credentials of the static testing_user(s).
* `tempest.conf` : main config file that store all the specs of your stack. Pay attention to :
  * `site_id` : Add here a custom identifier for the site (must be unique and the copied in the second config file for isolation tests[1])
  * `default_log_levels` : If the output is too verbose, you may need to adapt these values
  * `build_interval / build_timeout / ready_wait` : these high values where ok for a dev_stack, but may not for a production site
  * `[scenario]` : if you wish to create then upload a custom image (like cirros), you may need to download the files (img,ami,ari,aki) to your computer first...
  * `[service_available]` : activate or desactivate the services according to your site
  * `[auth]:test_accounts_file` : the path to the file has to be like "../config/account.yaml" (relative to the tempest dir)

Once the config is done, simply run the init script :
```
tools/init.sh
```
This script will init and update the submodule plus create some links to the custom scripts and check the necessary binaries on your system.

Regarding the running system, it will try to install the required dependencies via yum or apt (python-virtualenv at least).

If only you have `sudo`, you'll be prompted for your password to auto-install the dependancies. So check the script output...

If not, you'll have to install the packages manually.

This has been successfully tested on Centos7, Ubuntu14 and Debian8.

Once the script has run, you can launch `./check_openstack.sh -- tempest.api.fgcloud.test_basic_scenario` or any other tempest test :)

Feel free to report any problem you may encounter on github !

[1] See https://github.com/FranceGrilles/cloud-security.git
