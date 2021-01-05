import dobiss
import time
import sys

DEFAULT_IP = "192.168.1.118"
DEFAULT_PORT = 10001

# IP address of the installation
ip = DEFAULT_IP
if len(sys.argv) > 1:
    ip = sys.argv[1]

# TCP port
port = DEFAULT_PORT
if len(sys.argv) > 2:
    port = sys.argv[2]

d = dobiss.DobissSystem(ip, port)
d.importFullInstallation()
d.requestAllStatus()

while True:
    time.sleep(1)
    d.requestAllStatus()
    print(time.time())
    print(d.values)
