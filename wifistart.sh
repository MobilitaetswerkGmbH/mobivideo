#!/bin/bash

# Redundant stops to make sure services are not running
echo "Stopping network services (if running)..."
/bin/systemctl stop hostapd.service
/bin/systemctl stop dnsmasq.service
/bin/systemctl stop dhcpcd.service

# Make sure no uap0 interface exists (this generates an error; we could probably use an if statement to check if it exists first)
echo "Removing uap0 interface..."
#iw dev uap0 del
sleep 5

# Add uap0 interface (this is dependent on the wireless interface being called wlan0, which it may not be in Stretch)
echo "Adding uap0 interface..."
/sbin/rfkill unblock wifi
/sbin/iw dev wlan0 interface add uap0 type __ap

# Bring up uap0 interface. Commented out line may be a possible alternative to using dhcpcd.conf to set up the IP address.
#ifconfig uap0 192.168.70.1 netmask 255.255.255.0 broadcast 192.168.70.255
/sbin/ifconfig uap0 up
# Start hostapd.
echo "Starting hostapd service..."
/bin/systemctl start hostapd.service
sleep 1

# Start dhcpcd.
echo "Starting dhcpcd service..."
/bin/systemctl start dhcpcd.service
sleep 1

echo "Starting dnsmasq service..."
/bin/systemctl start dnsmasq.service

/sbin/iw dev wlan0 set power_save off
echo "wifistart DONE"
