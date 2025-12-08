from machine import Pin
import sys
import time

# -----------------------------
#  GPIO CONFIG
# -----------------------------
# List of GPIO numbers you want to control.
# You can trim this list to only the pins you actually use.
ALLOWED_PINS = list(range(0, 29))  # GPIO 0..28

pins = {}
pin_state = {}

for n in ALLOWED_PINS:
    try:
        p = Pin(n, Pin.OUT)
        p.value(0)          # start LOW
        pins[n] = p
        pin_state[n] = 0
    except Exception:
        # Some pins might not be available; just skip them
        pass


def make_status_string():
    # Example: STATE P0=0 P1=1 P2=0 ...
    parts = []
    for n in sorted(pin_state.keys()):
        parts.append("P{}={}".format(n, pin_state[n]))
    return "STATE " + " ".join(parts)


print("Ready.")
print("Commands:")
print("  GPIO <pin> <0|1>    -> set pin LOW/HIGH")
print("  ALL <0|1>           -> set all pins LOW/HIGH")
print("  STATUS              -> show all pin states")

while True:
    line = sys.stdin.readline()
    if not line:
        # Allow a tiny delay to avoid busy-looping
        time.sleep_ms(10)
        continue

    line = line.strip()
    if not line:
        continue

    parts = line.split()
    cmd = parts[0].upper()

    # ------------------------------------------
    # STATUS
    # ------------------------------------------
    if cmd == "STATUS":
        print(make_status_string())
        continue

    # ------------------------------------------
    # ALL <0|1>
    # ------------------------------------------
    if cmd == "ALL" and len(parts) == 2:
        try:
            val = int(parts[1])
        except ValueError:
            print("ERROR Invalid value (use 0 or 1)")
            continue

        if val not in (0, 1):
            print("ERROR Invalid value (use 0 or 1)")
            continue

        for n, p in pins.items():
            p.value(val)
            pin_state[n] = val
        print("OK", make_status_string())
        continue

    # ------------------------------------------
    # GPIO <pin> <0|1>
    # ------------------------------------------
    if cmd == "GPIO" and len(parts) == 3:
        try:
            pin_num = int(parts[1])
            val = int(parts[2])
        except ValueError:
            print("ERROR Invalid arguments (use: GPIO <pin> <0|1>)")
            continue

        if pin_num not in pins:
            print("ERROR Unknown pin")
            continue

        if val not in (0, 1):
            print("ERROR Invalid value (use 0 or 1)")
            continue

        pins[pin_num].value(val)
        pin_state[pin_num] = val
        print("OK P{}={} {}".format(pin_num, val, make_status_string()))
        continue

    # ------------------------------------------
    # Unknown / malformed command
    # ------------------------------------------
    print("ERROR Unknown command")
