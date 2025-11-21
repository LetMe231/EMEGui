from serialSwitch import SerialSwitch
import time

PORT = "COM4"  # <-- CHANGE to your real working COM port

sw = SerialSwitch(PORT)

print("Asking for STATUS...")
resp = sw.status()
print("STATUS RESP:", repr(resp))

print("Setting S1 to 1...")
resp = sw.set(1, "1")
print("SET RESP:", repr(resp))

time.sleep(0.5)

print("Setting S1 to 2...")
resp = sw.set(1, "2")
print("SET RESP:", repr(resp))

sw.close()
print("Done.")
