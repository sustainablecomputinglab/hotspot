## 0. Background 
While automated server hopping is a generic mechanism, HotSpot is currently designed for applications that can run inside a [Linux container](https://linuxcontainers.org/) and be hosted on [Amazon EC2 spot instances](https://aws.amazon.com/ec2/spot/). The application should perform all its disk and network IO using dedicated EBS drive and ENI interface (as these need to be migrated along with the container).

## 1. Building a HotSpot-enabled AMI 
To create an HotSpot-enabled AMI from scratch, boot up an EC2 instance with the chosen version of Linux (commands shown here are for Ubuntu) and then install the essential software packages (LXC, CRIU, Boto3, bridge-utils). Additionally, we configure the startup sequence to trigger a HotSpot setup script upon completing the boot up, and enable iproute to allow LXC to communicate to the external world via the host instance.
 
```bash
sudo apt-get update
sudo apt-get install linux-image-extra-`uname -r`
sudo apt-get install criu lxc1 python-pip bridge-utils
sudo apt-get remove lxd
sudo pip install --upgrade pip
sudo pip install boto3
sudo echo "2 eth1_rt" >> /etc/iproute2/rt_tables
scp hotSpot-code-dir to /home/ubuntu/hotSpot
sudo add /home/ubuntu/hotSpot/scripts/hotSpotSetup.sh to </etc/rc.local>
```

Finally, stop the EC2 instance and save its snapshot as the new AMI.
```bash
ec2-create-image instance_id --name "AMI-HOTSPOT" --region REGION-ID
```

## 2. VPC and network setup
EC2 requires the instances to be within a VPC in order to use ENIs with public-IP. The following set of CLIs document creating a VPC followed by a subnet, a security group, a gateway, a routing table all of which are associated with the VPC.

```shell
ec2-create-vpc --region REGION-ID 10.10.10.0/24
ec2-create-group hotspot -d "hotspot" -c VPC-ID --region REGION-ID
ec2-authorize SG-ID -P all --region REGION-ID
ec2-create-subnet -c VPC-ID --region REGION-ID -i 10.10.10.0/24
ec2-create-internet-gateway --region REGION-ID
ec2-attach-internet-gateway IGW-ID -c VPC-ID --region REGION-ID
ec2-create-route-table VPC-ID --region REGION-ID
ec2-create-route RTB-ID -r 0.0.0.0/0 -g IGW-ID --region REGION-ID
ec2-associate-route-table RTB-ID -s SUBNET-ID --region REGION-ID
```

Next step is to allocate an ENI and associate it with a public IP address. Source-check is disabled to let the instance send packets with different MAC address than what was initially associated with the interface (may be fixed more elegantly, not sure).

```shell
ec2-create-network-interface -d "hotspot-eni" -g SG-ID  --private-ip-address 
ec2-allocate-address --region REGION-ID -d "hotspot-public-ip" 
ec2-associate-address -a IP-ALLOC-ID -n ENI-ID --region REGION-ID
ec2-modify-network-interface-attribute ENI-ID --source-dest-check false --region REGION-ID
```

## 3. LXC and disk setup
Create an EBS volume, attach it to an instance and format appropriately.

```shell
ec2-create-volume -s SIZE -z ZONE-ID -t TYPE --region REGION-ID
sudo mkfs -t ext4 /dev/xvdh
```
Next, create a LXC container on this disk, which would be used to host the user application. An example LXC config is [here](https://github.com/umass-sustainablecomputinglab/hotspot/tree/master/code/config/lxc.config), which handles setting up of the root filesystem on the EBS disk, setting up CRIU specific parameters, and configuring the network to operate in bridge mode. Finally, copy the application into LXC filesystem.

```shell
sudo mount /dev/xvdh /var/lib/lxc
sudo lxc-create -n hotSpotLXC -t ubuntu
sudo cp lxc.config /var/lib/lxc/hotSpotLXC/
sudo cp br0.cfg /etc/network/interfaces.d/
sudo cp application.tar.gz /var/lib/lxc/hotSpotLXC/rootfs/home/ubuntu/
```

## 4. Putting it all together
Instantiate an EC2 server with the prebuilt HotSpot AMI. Setup AWS credentials in `~/.aws/credentials`, which are required to invoke AWS APIs.
```shell
ec2-run-instances AMI-HOTSPOT -k PUBLIC-KEY -t VM-TYPE -g SG-ID -s SUBNET-ID --region REGION-ID --associate-public-ip-address true -n 1
```

Attach the EBS disk and ENI interface
```shell
ec2-attach-volume VOL-ID -i INST-ID -d /dev/sdh --region REGION-ID
ec2-attach-network-interface ENI-ID --region REGION-ID -i INST-ID -d 1
```

The preconfigured HotSpot startup script will trigger automatically but will terminate since we haven't yet setup the application and its parameters. The first step is to populate the EBS/ENI/instance info in `/homt/ubuntu/hotSpot/controller/config`. Next, start the LXC container, login via serial console, and launch the user applicaiton. Finally, we start the HotSpot controller manually and it takes over the control.

```shell
sudo lxc-console -n hotSpotLXC
[lxc-bash]# nohup ./application &
python /home/ubuntu/hotSpot/scripts/hotSpotSetup.sh
```

