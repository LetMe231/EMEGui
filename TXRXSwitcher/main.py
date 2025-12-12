from machine import Pin
import sys
import time

# -----------------------------
#  GPIO CONFIG
# -----------------------------
S1_1 = Pin(20, Pin.OUT)
S1_2 = Pin(21, Pin.OUT)
S2_1 = Pin(19, Pin.OUT)
S2_2 = Pin(18, Pin.OUT)
S3_1 = Pin(17, Pin.OUT)
S3_2 = Pin(16, Pin.OUT)

coils = {
    "S1_1": S1_1, "S1_2": S1_2,
    "S2_1": S2_1, "S2_2": S2_2,
    "S3_1": S3_1, "S3_2": S3_2,
}

# -----------------------------
#  MAIN LOGIC
# -----------------------------

COIL_OFF = 0
COIL_ON  = 1

# Track last commanded state
switch_state = {
    "S1": "1",
    "S2": "1",
    "S3": "1"
}

# Turn all coils OFF at startup
for c in coils.values():
    c.value(COIL_OFF)

def pulse(coil_pin):
    print("DEBUG pulsing GPIO", coil_pin)
    coil_pin.value(COIL_ON)
    time.sleep_ms(50)
    coil_pin.value(COIL_OFF)

def set_switch(sid, side):
    # sid: "S1", "S2", "S3"
    # side: "1" or "1"
    pin_name = f"{sid}_{side}"
    if pin_name not in coils:
        return "ERROR"
    print("DEBUG set_switch:", sid, side, "pin:", pin_name)
    # Safety: make sure opposite coil is OFF
    if side == "1":
        coils[f"{sid}_2"].value(COIL_OFF)
    else:
        coils[f"{sid}_1"].value(COIL_OFF)

    pulse(coils[pin_name])
    switch_state[sid] = side
    return "OK"

def make_status_string():
    # Example: STATE S1=1 S2=2 S3=1
    return "STATE " + " ".join(f"{k}={v}" for k, v in switch_state.items())

print("Ready: commands SET S1_1 | SET S1_2 | SET S2_1 | ... | SET S3_2 | STATUS")

while True:
    line = sys.stdin.readline().strip().upper()
    if not line:
        continue

    if line == "STATUS":
        print(make_status_string())
        continue

    if line.startswith("SET "):
        try:
            _, sw = line.split()
            sid, side = sw.split("_")   # "S1", "1"
            if sid in ["S1", "S2", "S3"] and side in ["1", "2"]:
                result = set_switch(sid, side)
                print(result, make_status_string())
            else:
                print("ERROR Invalid switch")
        except Exception:
            print("ERROR Format")
    else:
        # ignore noise / unknown commands
        continue
