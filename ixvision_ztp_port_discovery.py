###############################################################################
#
# Zero-Touch Automation utility for Ixia Vision Network Packet Brokers
#
# File: ixvision_ztp_port_discovery.py
# Author: Alex Bortok (https://github.com/bortok)
#
# Description: Perform initial NPB port discovery.
# End goal is to have a system with LLDP neighbours being observed for further ZTP configuration steps
# 1. Perform port discovery - cycle through all supported port speeds to brning all possible links up
# 2. Disable all the ports that stayed down, tag the ports that came up as configured by ZTP
#
# COPYRIGHT 2018 - 2019 Keysight Technologies.
#
# This code is provided under the MIT license.  
# You can find the complete terms in LICENSE.txt
#
###############################################################################

from ksvisionlib import *

def discover_ports(host_ip, port, username, password, keyword=''):

    nto = VisionWebApi(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_ztp_debug.log")

    discoveredPortList = {}

    # Enumerate disabled ports - we are not touching anything that can already carry traffic
    searchTerms = {'enabled':False}
    if keyword != None and keyword != '':
        # Limit ZTP scope by a keyword if provided
        searchTerms = {"keywords":[keyword],'enabled':False}
        
    for ntoPort in nto.searchPorts(searchTerms):
        ntoPortDetails = nto.getPort(str(ntoPort['id']))
        discoveredPortList[ntoPort['id']] = {'name': ntoPortDetails['default_name'], 'type': 'port', 'ZTPSucceeded': False, 'details': ntoPortDetails}
        
    if len(discoveredPortList) == 0:
        return
    
    f = open(host_ip + '_pre_ztp_config.txt', 'w')
    f.write(json.dumps(discoveredPortList))
    f.close()

    # TODO Disconnect all the filters from the ports in scope
    
    # Start with 100G and FEC ON
    print('')
    print("Initiating 100G port discovery for QSFP28+ media type, with Forward Error Correction set to ON")
    print('')
    enabled_some_ports = False
    media_type = 'QSFP28'
    fec_type = 'RS_FEC'
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        if port['details']['media_type'] == media_type:
            if port['details']['mode'] == 'NETWORK' and port['details']['forward_error_correction_settings']['enabled']:
                # Enable such ports
                if 'enabled' in port['details']:
                    nto.modifyPort(str(port_id), {'enabled': True})
                    print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                    enabled_some_ports = True
            else:
                if port['details']['mode'] != 'NETWORK':
                    # Convert such ports to NETWORK
                    nto.modifyPort(str(port_id), {'mode': 'NETWORK'})
                    print("Converted port %s:%s to NETWORK" % (host_ip, port['details']['default_name']))
                if not port['details']['forward_error_correction_settings']['enabled']:
                    # Enable FEC
                    nto.modifyPort(str(port_id), {'forward_error_correction_settings': {'enabled': True, 'fec_type': fec_type}})
                    print("Enabled FEC on %s:%s" % (host_ip, port['details']['default_name']))
                # Validate new settings took effect
                portDetails = nto.getPort(str(port_id))
                if portDetails['mode'] == 'NETWORK' and portDetails['forward_error_correction_settings']['enabled']:
                    # Enable the port
                    if 'enabled' in port['details']:
                        nto.modifyPort(str(port_id), {'enabled': True})
                        print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                        enabled_some_ports = True
                    
    # Pause the thread to give the ports a chance to come up
    if enabled_some_ports:
        print('Paused for port status change to propagate...')
        time.sleep(10)
    
        # Collect link status for ports in scope
        for port_id in discoveredPortList:
            port = discoveredPortList[port_id]
            ntoPortDetails = nto.getPort(str(port_id))
            print("Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
            if ntoPortDetails['link_status']['link_up']:
                print('UP')
                discoveredPortList[port_id] = {'ZTPSucceeded': True}
            else:
                print('DOWN')
                discoveredPortList[port_id] = {'ZTPSucceeded': False}
            # Update the list with the latest config and status
            discoveredPortList[port_id]['details'] = ntoPortDetails

    # Stay on 100G, try FEC OFF for ports that didn't come up
    print('')
    print("Continuing 100G port discovery for QSFP28+ media type, now trying with Forward Error Correction set to OFF")
    print('')
    enabled_some_ports = False
    media_type = 'QSFP28'
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        if port['details']['media_type'] == media_type and not port['details']['link_status']['link_up']:
            if port['details']['mode'] == 'NETWORK' and not port['details']['forward_error_correction_settings']['enabled']:
                # Enable such ports
                if 'enabled' in port['details']:
                    nto.modifyPort(str(port_id), {'enabled': True})
                    print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                    enabled_some_ports = True
            else:
                if port['details']['mode'] != 'NETWORK':
                    # Convert such ports to NETWORK
                    nto.modifyPort(str(port_id), {'mode': 'NETWORK'})
                    print("Converted port %s:%s to NETWORK" % (host_ip, port['details']['default_name']))
                if port['details']['forward_error_correction_settings']['enabled']:
                    # Disable FEC
                    nto.modifyPort(str(port_id), {'forward_error_correction_settings': {'enabled': False}})
                    print("Disabled FEC on %s:%s" % (host_ip, port['details']['default_name']))
                # Validate new settings took effect
                portDetails = nto.getPort(str(port_id))
                if portDetails['mode'] == 'NETWORK' and not portDetails['forward_error_correction_settings']['enabled']:
                    # Enable the port
                    if 'enabled' in port['details']:
                        nto.modifyPort(str(port_id), {'enabled': True})
                        print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                        enabled_some_ports = True
                    
    # Pause the thread to give the ports a chance to come up
    if enabled_some_ports:
        print('Paused for port status change to propagate...')
        time.sleep(10)
    
        # Collect link status for ports in scope
        for port_id in discoveredPortList:
            port = discoveredPortList[port_id]
            ntoPortDetails = nto.getPort(str(port_id))
            print("Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
            if ntoPortDetails['link_status']['link_up']:
                print('UP')
                discoveredPortList[port_id] = {'ZTPSucceeded': True}
            else:
                print('DOWN')
                discoveredPortList[port_id] = {'ZTPSucceeded': False}
            # Update the list with the latest config and status
            discoveredPortList[port_id]['details'] = ntoPortDetails

    # Now try 40G
    print('')
    print("Initiating 40G port discovery for QSFP+ media type")
    print('')
    enabled_some_ports = False
    media_type = 'QSFP_PLUS_40G'
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        if port['details']['media_type'] == media_type and not port['details']['link_status']['link_up']:
            if port['details']['mode'] == 'NETWORK':
                # Enable such ports
                if 'enabled' in port['details']:
                    nto.modifyPort(str(port_id), {'enabled': True})
                    print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                    enabled_some_ports = True
            else:
                if port['details']['mode'] != 'NETWORK':
                    # Convert such ports to NETWORK
                    nto.modifyPort(str(port_id), {'mode': 'NETWORK'})
                    print("Converted port %s:%s to NETWORK" % (host_ip, port['details']['default_name']))
                # Validate new settings took effect
                portDetails = nto.getPort(str(port_id))
                if portDetails['mode'] == 'NETWORK':
                    # Enable the port
                    if 'enabled' in port['details']:
                        nto.modifyPort(str(port_id), {'enabled': True})
                        print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                        enabled_some_ports = True
                    
    # Pause the thread to give the ports a chance to come up
    if enabled_some_ports:
        print('Paused for port status change to propagate...')
        time.sleep(10)
    
        # Collect link status for ports in scope
        for port_id in discoveredPortList:
            port = discoveredPortList[port_id]
            ntoPortDetails = nto.getPort(str(port_id))
            print("Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
            if ntoPortDetails['link_status']['link_up']:
                print('UP')
                discoveredPortList[port_id] = {'ZTPSucceeded': True}
            else:
                print('DOWN')
                discoveredPortList[port_id] = {'ZTPSucceeded': False}
            # Update the list with the latest config and status
            discoveredPortList[port_id]['details'] = ntoPortDetails

    # Proceed to 10G
    print('')
    print("Initiating 10G port discovery for SFP+ media type")
    print('')
    enabled_some_ports = False
    media_type = 'SFP_PLUS_10G'
    link_settings = '10G_FULL'
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        if port['details']['media_type'] == media_type and port['details']['mode'] == 'NETWORK':
            # Enable such ports
            if 'enabled' in port['details']:
                nto.modifyPort(str(port_id), {'enabled': True})
                print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                enabled_some_ports = True
        else:
            if port['details']['media_type'] == 'SFP_1G':
                # Convert such ports to 10G
                nto.modifyPort(str(port_id), {'media_type': media_type,'link_settings': link_settings})
                print("Converted port %s:%s to 10G" % (host_ip, port['details']['default_name']))
            if port['details']['mode'] != 'NETWORK':
                # Convert such ports to NETWORK
                nto.modifyPort(str(port_id), {'mode': 'NETWORK'})
                print("Converted port %s:%s to NETWORK" % (host_ip, port['details']['default_name']))
            # Validate new settings took effect
            portDetails = nto.getPort(str(port_id))
            if portDetails['media_type'] == media_type and portDetails['mode'] == 'NETWORK':
                # Enable the port
                if 'enabled' in port['details']:
                    nto.modifyPort(str(port_id), {'enabled': True})
                    print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                    enabled_some_ports = True
                    
    # Pause the thread to give the ports a chance to come up
    if enabled_some_ports:
        print('Paused for port status change to propagate...')
        time.sleep(10)
    
        # Collect link status for ports in scope
        for port_id in discoveredPortList:
            port = discoveredPortList[port_id]
            ntoPortDetails = nto.getPort(str(port_id))
            print("Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
            if ntoPortDetails['link_status']['link_up']:
                print('UP')
                discoveredPortList[port_id] = {'ZTPSucceeded': True}
            else:
                print('DOWN')
                discoveredPortList[port_id] = {'ZTPSucceeded': False}
            # Update the list with the latest config and status
            discoveredPortList[port_id]['details'] = ntoPortDetails

    # Now go through the ports that are still down and change the media to 1G/AUTO
    print('')
    print("Initiating 1G/Auto port discovery for SFP+ media type")
    print('')
    enabled_some_ports = False
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        portDetails = port['details']
        if not portDetails['link_status']['link_up'] and portDetails['enabled'] and portDetails['media_type'] == 'SFP_PLUS_10G' \
            and portDetails['misc']['board_type'] != "EPIPHONE_100_MAIN": # 1G is not supported on E100
            nto.modifyPort(str(port_id), {'media_type': 'SFP_1G','link_settings': 'AUTO','mode': 'NETWORK'})
            print("Converted port %s:%s to 1G/Auto, NETWORK" % (host_ip, port['details']['default_name']))
            enabled_some_ports = True
        
    # Pause the thread to give the ports a chance to come up
    if enabled_some_ports:
        print('Paused for port status change to propagate...')
        time.sleep(10)
    
        # Collect link status for ports in scope
        # TODO DRY
        for port_id in discoveredPortList:
            port = discoveredPortList[port_id]
            ntoPortDetails = nto.getPort(str(port_id))
            print("Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
            if ntoPortDetails['link_status']['link_up']:
                print('UP')
                discoveredPortList[port_id] = {'ZTPSucceeded': True}
            else:
                print('DOWN')
                discoveredPortList[port_id] = {'ZTPSucceeded': False}
            # Update the list with the latest config and status
            discoveredPortList[port_id]['details'] = ntoPortDetails

    # Enable LLDP TX on all enabled ports in scope
    # For all ports where ZTP failed by this point, set them as network, 10G and disable
    print('')
    print("Finalizing port discovery...")
    print('')
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        portDetails = port['details']
        if port['ZTPSucceeded']:
            if 'lldp_receive_enabled' in portDetails: # check if this port has LLDP support before enabling it
                nto.modifyPort(str(port_id), {'lldp_receive_enabled': True, 'keywords': ['ZTP']})
                print("Enabled LLDP on port %s:%s" % (host_ip, port['details']['default_name']))
            else:
                print("Port %s:%s doesn't have LLDP RX capabilities" % (host_ip, port['details']['default_name']))
        else:
            nto.modifyPort(str(port_id), {'enabled': False, 'mode': 'NETWORK'})
            print("Converted port %s:%s to NETWORK and DISABLED" % (host_ip, port['details']['default_name']))



