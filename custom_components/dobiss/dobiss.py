"""
Helper module for communicating with a Dobiss home automation system.
"""

import socket
import logging
import time
from enum import IntEnum


class DobissSystem:

    def __init__(self, host, port):

        self._host = host
        self._port = port

        self.socket = None

        self.availableModules = [ ]
        self.modules = { }
        self.outputs = [ ]
        self.values = { }

    @property
    def host(self):
        """Return the host of this system."""
        return self._host

    @property
    def port(self):
        """Return the port of this system."""
        return self._port

    @property
    def lights(self):
        result = [ ]
        for output in self.outputs:
            if output['type'] == DobissSystem.OutputType.Light:
                result.append(output)

        return result

    def fans(self):
        result = [ ]
        for output in self.outputs:
            if output['type'] == DobissSystem.OutputType.Fan:
                result.append(output)

        return result

    def plugs(self):
        result = [ ]
        for output in self.outputs:
            if output['type'] == DobissSystem.OutputType.Plug:
                result.append(output)

        return result

    def connect(self, tryUntilSuccess=True):
        """Connect to a Dobiss system.
           Keeps trying to connect until it is successfully connected.
        """
        if not self.socket is None:
            return True

        success = False

        if tryUntilSuccess:
            # Keep connecting the TCP socket until success
            while self.socket is None:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.socket.connect((self.host, self.port))
                    success = True

                except socket.error:
                    self.socket = None
                    success = False
                    time.sleep(1) # Wait for 1 second

        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.socket.connect((self.host, self.port))
                success = True

            except socket.error:
                self.socket = None
                success = False

        return success


    def disconnect(self):
        """Disconnect from the connected Dobiss system.
        """
        if not self.socket is None:
            self.socket.close()
            self.socket = None


    def sendData(self, data):
        """Send data to a Dobiss system.
           Keeps trying to send the data until it is successful, reconnecting with the system if necessary.
        """
        dataSent = False
        #while not dataSent:
        try:
            self.socket.sendall(data)
            dataSent = True

        except socket.error:
            #disconnect()
            #connect()
            dataSent = False

        return dataSent


    def importFullInstallation(self):
        """Import the installation, all modules, their outputs and their status."""

        # Import installation
        self.importInstallation()

        # TEMP Hardcoded modules
        for moduleAddr in [1, 2, 3, 4, 5]:
            self.importModule(moduleAddr)

        # Outputs and their current value
        for moduleAddr, module in self.modules.items():
            self.importOutputs(module['address'], module['type'], module['outputCount'])
            self.requestStatus(module['address'], module['type'], module['outputCount'])


    def importInstallation(self):
        """Import the installation."""
        data = bytearray.fromhex("AF 0B 00 00 30 00 10 01 10 FF FF FF FF FF FF AF")
        self.sendData(data)

        original = self.socket.recv(len(data))
        padding = self.socket.recv((32 - (len(data) % 32)) % 32)
        installationData = self.socket.recv(16)
        padding = self.socket.recv((32 - (16 % 32)) % 32)

        # TODO Parse the installation


    class ModuleType(IntEnum):
        """The type of module."""
        Relais = 0x08
        Dimmer = 0x10
        V0_10 = 0x18

    def importModule(self, moduleAddr):
        """Import a module."""

        # Import the module
        #data = bytearray.fromhex("AF 10 FF " + chr(moduleAddr).encode('hex') + " 00 00 10 01 10 FF FF FF FF FF FF AF")
        data = bytearray.fromhex("AF 10 FF " + '{:02x}'.format(moduleAddr) + " 00 00 10 01 10 FF FF FF FF FF FF AF")
        self.sendData(data)

        original = self.socket.recv(len(data))
        padding = self.socket.recv((32 - (len(data) % 32)) % 32)
        moduleData = self.socket.recv(16)
        padding = self.socket.recv((32 - (16 % 32)) % 32)

        #moduleAddr = ord(moduleData[0])
        #moduleType = ord(moduleData[14])
        #master = ord(moduleData[2])
        moduleAddr = moduleData[0]
        moduleType = DobissSystem.ModuleType(moduleData[14])
        master = moduleData[2]
        masterLSB = master&1
        isMaster = (masterLSB == 1)

        # 12 outputs for relais, 4 for dimmers
        if moduleType == DobissSystem.ModuleType.Relais:
            outputCount = 12
        else:
            outputCount = 4

        # Cache the module
        self.modules[moduleAddr] = {
            'address': moduleAddr,
            'type': moduleType,
            'isMaster': isMaster,
            'outputCount': outputCount
        }


    class OutputType(IntEnum):
        """The type of output."""
        Light = 0x00
        Plug = 0x01
        Fan = 0x02
        Up = 0x03
        Down = 0x04

    def importOutputs(self, moduleAddr, moduleType, outputCount):
        """Import the outputs of a module."""

        # Import the module
        #data = bytearray.fromhex("AF 10 " + chr(moduleType).encode('hex') +  + chr(moduleAddr).encode('hex') + " 01 00 20 " + chr(outputCount).encode('hex') + " 20 FF FF FF FF FF FF AF")
        data = bytearray.fromhex("AF 10 " + '{:02x}'.format(moduleType.value) + '{:02x}'.format(moduleAddr) + " 01 00 20 " + '{:02x}'.format(outputCount) + " 20 FF FF FF FF FF FF AF")
        self.sendData(data)

        # <module.outputCount> lines of 32 bytes
        # Output names of 30 characters; convert byte array to string;
        # data[30] = icon type (0=light, 1=plug, 2=fan, 3=up, 4=down); data[31] = group index

        original = self.socket.recv(len(data))
        padding = self.socket.recv((32 - (len(data) % 32)) % 32)
        outputsData = self.socket.recv(32 * (outputCount + 1)) #
        # Note: no padding because we have lines of 32 bytes

        for outputIndex in range(0, outputCount):
            line = outputsData[outputIndex * 32 : (outputIndex + 1) * 32]
            outputName = line[0:30].strip().decode()
            outputType = DobissSystem.OutputType(line[30])
            groupIndex = line[31]

            # Cache the output
            self.outputs.append({
                'moduleAddress': moduleAddr,
                'index': outputIndex,
                'name': outputName,
                'type': outputType,
                'groupIndex': groupIndex
           })


    def requestStatus(self, moduleAddr, moduleType, outputCount):
        """Request the status of all outputs of a module."""

        # Request the status
        data = bytearray.fromhex("AF 01 " + '{:02x}'.format(moduleType.value) + '{:02x}'.format(moduleAddr) + " 00 00 00 01 00 FF FF FF FF FF FF AF")
        self.sendData(data)

        original = self.socket.recv(len(data))
        padding = self.socket.recv((32 - (len(data) % 32)) % 32)
        statusData = self.socket.recv(16) # One line of 16 bytes
        padding = self.socket.recv((32 - (16 % 32)) % 32)


        if not moduleAddr in self.values:
            self.values[moduleAddr] = [ ]

        for outputIndex in range(0, outputCount):
            value = statusData[outputIndex]

            # Cache the value
            if len(self.values[moduleAddr]) <= outputIndex:
                self.values[moduleAddr].append(value)
            else:
                self.values[moduleAddr][outputIndex] = value



    class Action(IntEnum):
        """The type of action."""
        TurnOff = 0x00
        TurnOn = 0x01
        Toggle = 0x02

    def setOn(self, moduleAddr, outputIndex, brightness = 100):
        """Switch an output on."""

        action = DobissSystem.Action.TurnOn
        self.sendAction(moduleAddr, outputIndex, action, brightness)

    def setOff(self, moduleAddr, outputIndex):
        """Switch an output off."""

        action = DobissSystem.Action.TurnOff
        self.sendAction(moduleAddr, outputIndex, action)

    def toggle(self, moduleAddr, outputIndex):
        """Toggle an output."""

        action = DobissSystem.Action.Toggle
        self.sendAction(moduleAddr, outputIndex, action)

    def sendAction(self, moduleAddr, outputIndex, action, value = 100, delayOn = 0xFF, delayOff = 0xFF, softDim = 0xFF, red = 0xFF):
        """Generic method to send an action to an output."""

        # Send the request
        headerData = bytearray.fromhex("AF 02 FF " + '{:02x}'.format(moduleAddr) + " 00 00 08 01 08 FF FF FF FF FF FF AF")
        self.sendData(headerData)

        # Note: no additional data is sent back
        original = self.socket.recv(len(headerData))
        padding = self.socket.recv((32 - (len(headerData) % 32)) % 32)

        requestData = bytes((moduleAddr, outputIndex, action.value, delayOn, delayOff, int(value), softDim, red))
        self.sendData(requestData)

        # Note: no additional data is sent back
        original = self.socket.recv(len(requestData))
        padding = self.socket.recv((32 - (len(requestData) % 32)) % 32)
