# monitoring-cloud
Collection of scripts to monitor IaaS Cloud (OpenStack, OpenNebula...) via libcloud API.

libcloud as a git submodule from https://github.com/apache/libcloud/

```
git submodule add https://github.com/apache/libcloud
```

## Goals
With access to the API services will try to :

* add/upload custom image (small one like cirros or tinylinux)
* create a tiny node with that image and a custom SSH-key
* create/attach a public IP address
* create/attach a permanent storage
* login using SSH-key
  * mount permanent storage
  * check writing and reading from the storage
  * unmount, (shutdown), logout
* destroy storage, destroy node, delete image, verify
* 
