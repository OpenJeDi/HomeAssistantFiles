"""
Helper module for communicating with a Dobiss home automation system.
"""

import socket
import logging
import asyncio
from enum import IntEnum

RECV_SIZE = 1024
MAX_NUM_RETRIES = 10
TIMEOUT = 1  # We can use a short timeout on the LAN
RETRY_DELAY = 1  # Set the delay between retries in seconds

_LOGGER = logging.getLogger(__name__)


class DobissSystem:

    def __init__(self, host, port):

        self._host = host
        self._port = port
        self._connected = False

        self.socket = None
        # self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.settimeout(TIMEOUT)
        self.recvBuffer = bytearray()

        self.availableModules = []
        self.modules = {}
        self.outputs = []
        self.values = {}

    @property
    def host(self):
        """Return the host of this system."""
        return self._host

    @property
    def port(self):
        """Return the port of this system."""
        return self._port

    @property
    def connected(self):
        """True if the socket is connected"""
        return self._connected

    @property
    def lights(self):
        result = []
        for output in self.outputs:
            if output['type'] == DobissSystem.OutputType.Light:
                result.append(output)

        return result

    @property
    def fans(self):
        result = []
        for output in self.outputs:
            if output['type'] == DobissSystem.OutputType.Fan:
                result.append(output)

        return result

    @property
    def plugs(self):
        result = []
        for output in self.outputs:
            if output['type'] == DobissSystem.OutputType.Plug:
                result.append(output)

        return result

    async def connect(self):
        """Connect to a Dobiss system.
           Keeps trying to connect until it is successfully connected.
        """
        retry_delay = 1  # Initial delay in seconds
        retries = 0
        while not self._connected and retries < MAX_NUM_RETRIES:
            try:
                _LOGGER.info(f"connect through connect_logic")
                self.connect_logic()
            except socket.error as e:
                _LOGGER.error(f"Dobiss socket error while trying to connect: {str(e)}")
                # self.disconnect()
                self._connected = False
                retries += 1
                if retries < MAX_NUM_RETRIES:
                    _LOGGER.debug(f"Retrying in {retry_delay} seconds...")
                    # time.sleep(retry_delay)
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    # self.connect_logic()
                else:
                    _LOGGER.error("Maximum retry attempts reached. Connection failed.")
                    break

    def connect_logic(self):
        _LOGGER.info(f"Connecting to Dobiss system at IP {self.host} and port {self.port}")
        # self.socket.connect((self.host, self.port))
        self.socket = socket.create_connection((self.host, self.port))
        self._connected = True
        # self.socket.settimeout(None)
        _LOGGER.info("Connected to Dobiss system.")

    def disconnect(self):
        """Disconnect from the connected Dobiss system.
        """
        _LOGGER.error("disconnecting from Dobiss system")

        try:
            self.socket.close()
        except socket.error as e:
            _LOGGER.error(f"Dobiss socket error {str(e)}")
        finally:
            self._connected = False

    async def sendData(self, data):
        _LOGGER.debug(f"sendData {str(data)}")
        """Send data to a Dobiss system.
           Keeps trying to send the data until it is successful, reconnecting with the system if necessary.
        """
        # dataSent = False
        retry = True
        num_retries = 0

        # while retry:
        try:
            self.socket.sendall(data)
            # retry = False
            return True
        except socket.error as e:
            _LOGGER.error(f"Dobiss socket error on sending data {str(e)}")
            await self.reconnect(data)
            # num_retries += 1
            # if num_retries >= MAX_NUM_RETRIES:
            #     return False
            # time.sleep(RETRY_DELAY)  # Introduce a delay between retries # HA does not allow this
        # return False

    async def reconnect(self, data):
        _LOGGER.info(f"Dobiss for the reconnect")
        self.disconnect()
        await self.connect()
        if data:
            await self.sendData(data)

    def receiveResponse(self, sentDataSize, responseSize):
        """Receive response"""

        # Receive until we have enough data
        # The data consists of the sent data (padded to 32 bytes) and then the response data (padded to 32 bytes)
        sentDataPaddingSize = (32 - (sentDataSize % 32)) % 32
        responsePaddingSize = (32 - (responseSize % 32)) % 32
        totalSize = sentDataSize + sentDataPaddingSize + responseSize + responsePaddingSize

        numRetries = 0

        while (len(self.recvBuffer) < totalSize) and (numRetries < MAX_NUM_RETRIES):
            try:
                received_data = self.socket.recv(RECV_SIZE)

                if received_data:
                    self.recvBuffer += received_data
                    # print(f"Received from socket. Buffer is now length {len(self.recvBuffer)}")

            except socket.error as e:
                print(f"Dobiss socket error while receiving data: {str(e)}")
                return []

        # We first receive the original packet back
        # TODO Actually check the content
        # original = self.recvBuffer[:sentDataSize]

        # The actual response data
        responseData = bytearray()
        if responseSize > 0:
            start = sentDataSize + sentDataPaddingSize
            end = start + responseSize
            responseData = self.recvBuffer[start:end]

        # Remove the response from the buffer        
        self.recvBuffer = self.recvBuffer[totalSize:]

        return responseData

    async def importFullInstallation(self):
        """Import the installation, all modules, their outputs and their status."""

        # Import installation
        await self.importInstallation()

        # Import modules
        for moduleAddr in self.availableModules:
            await self.importModule(moduleAddr)

        # Outputs and their current value
        for moduleAddr, module in self.modules.items():
            await self.importOutputs(module['address'], module['type'], module['outputCount'])
            await self.requestStatus(module['address'], module['type'], module['outputCount'])

    async def importInstallation(self):
        """Import the installation."""
        data = bytearray.fromhex("AF 0B 00 00 30 00 10 01 10 FF FF FF FF FF FF AF")
        await self.sendData(data)

        installationData = self.receiveResponse(len(data), 16)

        if len(installationData) != 16:
            print(
                f"Invalid data received trying to import installation: received {len(installationData)} bytes instead of 16")
            return

        # Parse the installation
        self.availableModules = []

        # First 11 bytes (bits 0-81) contain whether or not there is a module with the specific address (1-82)
        for i in range(0, 82):
            byteNum = int(i / 8)
            bitNum = int(i % 8)
            hasModule = (installationData[byteNum] >> bitNum) & 1
            if hasModule:
                channelAddr = i + 1
                self.availableModules.append(channelAddr)

        print("Available modules: " + str(self.availableModules))

    class ModuleType(IntEnum):
        """The type of module."""
        Relais = 0x08
        Dimmer = 0x10
        V0_10 = 0x18

    async def importModule(self, moduleAddr):
        """Import a module."""

        # Import the module
        # data = bytearray.fromhex("AF 10 FF " + chr(moduleAddr).encode('hex') + " 00 00 10 01 10 FF FF FF FF FF FF AF")
        data = bytearray.fromhex("AF 10 FF " + f"{moduleAddr:02x}" + " 00 00 10 01 10 FF FF FF FF FF FF AF")
        await self.sendData(data)

        moduleData = self.receiveResponse(len(data), 16)

        if len(moduleData) != 16:
            print(f"Invalid data received trying to import module: received {len(moduleData)} bytes instead of 16")
            return

        # moduleAddr = ord(moduleData[0])
        # moduleType = ord(moduleData[14])
        # master = ord(moduleData[2])
        moduleAddr = moduleData[0]
        moduleType = DobissSystem.ModuleType(moduleData[14])
        master = moduleData[2]
        masterLSB = master & 1
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

        print(f"Module {moduleAddr} imported: " + str(self.modules[moduleAddr]))

    class OutputType(IntEnum):
        """The type of output."""
        Light = 0x00
        Plug = 0x01
        Fan = 0x02
        Up = 0x03
        Down = 0x04

    async def importOutputs(self, moduleAddr, moduleType, outputCount):
        """Import the outputs of a module."""

        # Import the module
        # data = bytearray.fromhex("AF 10 " + chr(moduleType).encode('hex') +  + chr(moduleAddr).encode('hex') + " 01 00 20 " + chr(outputCount).encode('hex') + " 20 FF FF FF FF FF FF AF")
        data = bytearray.fromhex(
            "AF 10 " + f"{moduleType.value:02x}" + f"{moduleAddr:02x}" + " 01 00 20 " + f"{outputCount:02x}" + " 20 FF FF FF FF FF FF AF")
        await self.sendData(data)

        # <module.outputCount> lines of 32 bytes
        # Output names of 30 characters; convert byte array to string;
        # data[30] = icon type (0=light, 1=plug, 2=fan, 3=up, 4=down); data[31] = group index
        outputsData = self.receiveResponse(len(data), 32 * outputCount)

        if len(outputsData) != 32 * outputCount:
            print(
                f"Invalid data received trying to import module: received {len(outputsData)} bytes instead of {32 * outputCount}")
            return

        for outputIndex in range(0, outputCount):
            line = outputsData[outputIndex * 32: (outputIndex + 1) * 32]
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

            print(f"Output imported: " + str(self.outputs[len(self.outputs) - 1]))

    async def requestStatus(self, moduleAddr, moduleType, outputCount):
        """Request the status of all outputs of a module."""

        # Request the status
        data = bytearray.fromhex(
            "AF 01 " + f"{moduleType.value:02x}" + f"{moduleAddr:02x}" + " 00 00 00 01 00 FF FF FF FF FF FF AF")
        await self.sendData(data)

        statusData = self.receiveResponse(len(data), 16)

        if len(statusData) != 16:
            print(f"Invalid data received trying to import module: received {len(statusData)} bytes instead of 16")
            return

        if not moduleAddr in self.values:
            self.values[moduleAddr] = []

        for outputIndex in range(0, outputCount):
            value = statusData[outputIndex]

            # Cache the value
            if len(self.values[moduleAddr]) <= outputIndex:
                self.values[moduleAddr].append(value)
            else:
                self.values[moduleAddr][outputIndex] = value

    async def requestAllStatus(self):
        """Request the status of all outputs of all modules."""

        for moduleAddr, module in self.modules.items():
            await self.requestStatus(module['address'], module['type'], module['outputCount'])

    class Action(IntEnum):
        """The type of action."""
        TurnOff = 0x00
        TurnOn = 0x01
        Toggle = 0x02

    async def setOn(self, moduleAddr, outputIndex, brightness=100):
        """Switch an output on."""
        _LOGGER.debug("setOn")
        action = DobissSystem.Action.TurnOn
        await self.sendAction(moduleAddr, outputIndex, action, brightness)

    async def setOff(self, moduleAddr, outputIndex):
        """Switch an output off."""
        _LOGGER.debug("setOff")
        action = DobissSystem.Action.TurnOff
        await self.sendAction(moduleAddr, outputIndex, action)

    async def toggle(self, moduleAddr, outputIndex):
        """Toggle an output."""
        _LOGGER.debug("toggle")
        action = DobissSystem.Action.Toggle
        await self.sendAction(moduleAddr, outputIndex, action)

    async def sendAction(self, moduleAddr, outputIndex, action, value=100, delayOn=0xFF, delayOff=0xFF, softDim=0xFF,
                   red=0xFF):
        """Generic method to send an action to an output."""
        _LOGGER.debug("sendAction")
        # Send the request header
        headerData = bytearray.fromhex("AF 02 FF " + f"{moduleAddr:02x}" + " 00 00 08 01 08 FF FF FF FF FF FF AF")
        await self.sendData(headerData)

        # Note: no additional data is sent back
        self.receiveResponse(len(headerData), 0)

        # Send the request data
        requestData = bytes((moduleAddr, outputIndex, action.value, delayOn, delayOff, int(value), softDim, red))
        await self.sendData(requestData)

        # Note: no additional data is sent back
        self.receiveResponse(len(requestData), 0)
