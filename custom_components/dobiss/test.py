import dobiss
import time

d = dobiss.DobissSystem("192.168.1.118", 10001)
d.importFullInstallation()
d.requestAllStatus()

while True:
    time.sleep(1)
    d.requestAllStatus()
    print(time.time())
    print(d.values)
