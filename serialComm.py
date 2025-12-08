import serial
import time

class SerialAntenna:
    def __init__(self, port, baudrate=9600):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.connected = self.ser.is_open
            try:
                self.az, self.el = self.read_md01_position()
            except TimeoutError:
                raise ConnectionError("Serial port not connected to MD-01 Controller")
            else:
                self.connected = self.ser.is_open
        except serial.SerialException:
            self.connected = False
        cmd = bytes(12)

    def status(self):
        return self.connected and self.ser.is_open

    def read_md01_position(self):
        """
        Send a SPID Rot 2 'Read position' command for MD-01.
        Calculate the Azimuth and Elevation from recieved Packet.

        returns: az and el of the Antenna.
        """
        if not self.connected:
            raise ConnectionError("Serial port not connected")
        cmd = bytes([0x57] +        # 'w' start bit
                    [0]*10 +        # 10 times 0 (would be az/el at send)
                    [0x1F, 0x20])   # command for read and stop bit
        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.1)
        frame = self.ser.read(12)
        if not frame or frame[0] != 0x57:
            raise TimeoutError("No valid frame received")
        az = frame[1]*100 + frame[2]*10 + frame[3]
        if len(frame) >= 5:
            az += frame[4]/10.0
        az -= 360
        el = 0.0
        if len(frame) >= 10:
            el = frame[6]*100 + frame[7]*10 + frame[8] + frame[9]/10.0
            el -= 360
        return az, el
    
    def build_rot2_set_command(self, az_deg, el_deg, ph=10, pv=10):
        """
        Build a SPID Rot 2 'SET position' command packet for MD-01.
        
        az_deg: target azimuth in degrees (float or int)
        el_deg: target elevation in degrees (float or int)
        ph: azimuth resolution (pulses per degree, default=2 → 0.5° per step)
        pv: elevation resolution (pulses per degree, default=2 → 0.5° per step)
        
        Returns: bytes ready to send
        """
        # Calculate pulses (controller expects values offset by +360)
        h_val = int(ph * (360 + az_deg))
        v_val = int(pv * (360 + el_deg))

        # Format as zero-padded ASCII digit strings (4 chars each)
        h_str = f"{h_val:04d}"
        v_str = f"{v_val:04d}"
        
        # Build packet
        packet = bytearray()
        packet.append(0x57)                       # 'W' start
        packet.extend(h_str.encode("ascii"))      # H1–H4
        packet.append(ph & 0xFF)                  # PH
        packet.extend(v_str.encode("ascii"))      # V1–V4
        packet.append(pv & 0xFF)                  # PV
        packet.append(0x2F)                       # K = SET position
        packet.append(0x20)                       # end (space)
        
        return bytes(packet)


    def send_rot2_set(self, ser, az_deg, el_deg):
        """
        Send a SET position command to MD-01 via Serial.

        ser: Open serial port.
        az_deg: target azimuth in degrees (float or int)
        el_deg: target elevation in degrees (float or int)
        """
        cmd = self.build_rot2_set_command(az_deg, el_deg)
        ser.reset_input_buffer()
        ser.write(cmd)
        
    def stopMovement(self):
        if self.connected:
            cmd = bytes([0x57] + [0]*10 + [0x0F, 0x20])
            self.ser.reset_input_buffer()
            self.ser.write(cmd)
        else:
            raise ConnectionError("Serial port not connected")

    def close(self):
        if self.connected:
            self.ser.close()
        else:
            raise ConnectionError("Serial port not connected")
