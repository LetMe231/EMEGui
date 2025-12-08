from serialSwitch import SerialSwitch
import time

PORT = "COM13"  # <-- CHANGE to your real working COM port

sw = SerialSwitch(PORT)

print("Asking for STATUS...")
resp = sw.status()
print("STATUS RESP:", repr(resp))

print("Setting S1 to 1 (10 seconds)...")
resp = sw.set(1, "1")
print("SET RESP:", repr(resp))
time.sleep(10)  # <-- plenty of time to measure S1=1

print("Setting S1 to 2 (10 seconds)...")
resp = sw.set(1, "2")
print("SET RESP:", repr(resp))
time.sleep(10)  # <-- plenty of time to measure S1=2

sw.close()
print("Done.")
