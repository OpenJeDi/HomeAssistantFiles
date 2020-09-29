import dobiss

d = dobiss.DobissSystem("192.168.1.116", 10001)
d.importFullInstallation()
d.requestAllStatus()
