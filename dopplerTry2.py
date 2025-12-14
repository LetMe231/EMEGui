import numpy as np
import matplotlib.pyplot as plt
from skyfield.api import load, wgs84
from datetime import datetime, timezone, timedelta  # <-- timedelta ergänzt

# ================== CONFIG ==================

STATION_LAT = 47.2237270     # deg
STATION_LON = 8.8176838      # deg
STATION_ELV = 466.63         # meters

# RF frequency
FREQ_HZ = 1296e6

# Day to simulate (UTC)
YEAR  = 2025
MONTH = 12
DAY   = 14
now = datetime.now(timezone.utc)
YEAR    = now.year
MONTH   = now.month
DAY     = now.day

# Time resolution
POINTS_PER_DAY = 24 * 12


# ================== CORE CALC ==================

def compute_eme_day():
    # Load time scale and ephemeris
    ts = load.timescale()
    # Times over one UTC day
    hours = np.linspace(0, 24, POINTS_PER_DAY)
    t = ts.utc(YEAR, MONTH, DAY, hours)

    # JPL ephemeris
    eph = load('de440s.bsp')
    earth = eph['earth']
    moon  = eph['moon']

    # Station
    station = earth + wgs84.latlon(STATION_LAT, STATION_LON, elevation_m=STATION_ELV)

    distances_km = []
    range_rates_m_s = []
    doppler_2way_Hz = []
    moon_up_mask = []

    c = 299_792_458.0  # m/s

    for ti in t:
        # Vector station -> moon
        astrometric = station.at(ti).observe(moon)

        # Distance (topocentric)
        distance = astrometric.distance().km   # km
        distances_km.append(distance)

        # Position & velocity (km, km/s) to get range rate
        r_km, v_km_s = astrometric.position.km, astrometric.velocity.km_per_s
        r_vec = np.array(r_km)
        v_vec = np.array(v_km_s)

        R_km = np.linalg.norm(r_vec)
        r_hat = r_vec / R_km
        Rdot_km_s = np.dot(v_vec, r_hat)   # km/s
        Rdot_m_s = Rdot_km_s * 1000.0      # m/s
        range_rates_m_s.append(Rdot_m_s)

        # 2-way Doppler: up + down
        doppler_2way = -2.0 * (Rdot_m_s / c) * FREQ_HZ
        doppler_2way_Hz.append(doppler_2way)

        # Check if Moon is above horizon
        alt, az, _ = astrometric.apparent().altaz()
        moon_up_mask.append(alt.degrees > 0.0)

    return np.array(hours), np.array(distances_km), np.array(range_rates_m_s), np.array(doppler_2way_Hz), np.array(moon_up_mask)

def compute_eme_interval(duration_hours=1.0, step_minutes=1.0):
    ts = load.timescale()
    eph = load('de440s.bsp')
    earth = eph['earth']
    moon  = eph['moon']
    station = earth + wgs84.latlon(STATION_LAT, STATION_LON, elevation_m=STATION_ELV)

    # time array: from 0 to duration_hours, in step_minutes
    minutes = np.arange(0, duration_hours * 60 + 1e-9, step_minutes)
    hours   = minutes / 60.0
    t = ts.utc(YEAR, MONTH, DAY, hours)

    distances_km = []
    Rdot_m_s     = []
    doppler_Hz   = []
    moon_up      = []

    c = 299_792_458.0

    for ti in t:
        astrometric = station.at(ti).observe(moon)

        distance = astrometric.distance().km
        distances_km.append(distance)

        r_km, v_km_s = astrometric.position.km, astrometric.velocity.km_per_s
        r_vec = np.array(r_km)
        v_vec = np.array(v_km_s)

        R_km = np.linalg.norm(r_vec)
        r_hat = r_vec / R_km
        Rdot_km_s = np.dot(v_vec, r_hat)
        Rdot = Rdot_km_s * 1000.0
        Rdot_m_s.append(Rdot)

        doppler = -2.0 * (Rdot / c) * FREQ_HZ
        doppler_Hz.append(doppler)

        alt, az, _ = astrometric.apparent().altaz()
        moon_up.append(alt.degrees > 0)

    return hours, np.array(distances_km), np.array(Rdot_m_s), np.array(doppler_Hz), np.array(moon_up)


def compute_eme_interval_seconds(duration_seconds=2.0, step_seconds=0.1):

    ts = load.timescale()
    eph = load('de440s.bsp')
    earth = eph['earth']
    moon  = eph['moon']
    station = earth + wgs84.latlon(STATION_LAT, STATION_LON, elevation_m=STATION_ELV)

    # Time offsets in seconds
    seconds = np.arange(0.0, duration_seconds + 1e-9, step_seconds)

    # Current UTC time as the start
    now = datetime.now(timezone.utc)

    # Build a Time ARRAY: 'second' argument is now.second + offsets
    t = ts.utc(
        now.year,
        now.month,
        now.day,
        now.hour,
        now.minute,
        now.second + now.microsecond / 1e6 + seconds
    )
    # 't' is now a Skyfield Time array

    distances_km = []
    Rdot_m_s     = []
    doppler_Hz   = []
    f_rx_Hz      = []
    moon_up      = []

    c = 299_792_458.0

    for ti in t:
        astrometric = station.at(ti).observe(moon)

        distance = astrometric.distance().km
        distances_km.append(distance)

        r_km, v_km_s = astrometric.position.km, astrometric.velocity.km_per_s
        r_vec = np.array(r_km)
        v_vec = np.array(v_km_s)

        R_km = np.linalg.norm(r_vec)
        r_hat = r_vec / R_km

        Rdot_km_s = np.dot(v_vec, r_hat)
        Rdot = Rdot_km_s * 1000.0
        Rdot_m_s.append(Rdot)

        doppler = -2.0 * (Rdot / c) * FREQ_HZ
        doppler_Hz.append(doppler)

        f_rx = FREQ_HZ + doppler
        f_rx_Hz.append(f_rx)

        alt, az, _ = astrometric.apparent().altaz()
        moon_up.append(alt.degrees > 0.0)

    return (
        seconds,                          # time offsets (s) from "now"
        np.array(distances_km),
        np.array(Rdot_m_s),
        np.array(doppler_Hz),
        np.array(f_rx_Hz),
        np.array(moon_up),
    )

# ========= NEU: Hilfsfunktion für Doppler an einem Zeitpunkt =========

def _doppler_2way_for_time(t, earth, moon, station):
    """2-way Doppler in Hz für einen gegebenen Skyfield-Time t."""
    astrometric = station.at(t).observe(moon)

    r_km, v_km_s = astrometric.position.km, astrometric.velocity.km_per_s
    r_vec = np.array(r_km)
    v_vec = np.array(v_km_s)

    R_km = np.linalg.norm(r_vec)
    r_hat = r_vec / R_km
    Rdot_km_s = np.dot(v_vec, r_hat)
    Rdot_m_s = Rdot_km_s * 1000.0

    c = 299_792_458.0
    doppler_2way = -2.0 * (Rdot_m_s / c) * FREQ_HZ
    return doppler_2way

def doppler_change_at_utc(hour_utc, minute_utc=0, span_s=10.0):
    """
    Bestimmt die Änderungsrate des 2-way Dopplers um eine gegebene UTC-Uhrzeit
    an dem Tag YEAR/MONTH/DAY.

    Übergabe:
      hour_utc, minute_utc : z.B. 10, 30 für 10:30 UTC
      span_s               : Abstand zwischen den beiden Stützstellen (Symmetrisch um die Mitte)

    Rückgabe:
      rate_Hz_per_s   : Doppler-Änderung in Hz/s
      rate_Hz_per_min : Doppler-Änderung in Hz/min
      d_center_Hz     : Doppler exakt zur angegebenen Zeit
    """

    ts = load.timescale()
    eph = load('de440s.bsp')
    earth = eph['earth']
    moon  = eph['moon']
    station = earth + wgs84.latlon(STATION_LAT, STATION_LON, elevation_m=STATION_ELV)

    # Zeit genau am gewünschten UTC-Zeitpunkt
    center_dt = datetime(
        YEAR, MONTH, DAY,
        hour_utc, minute_utc, 0,
        tzinfo=timezone.utc
    )

    # Zwei Zeitpunkte symmetrisch um center_dt
    dt_before = center_dt - timedelta(seconds=span_s / 2.0)
    dt_after  = center_dt + timedelta(seconds=span_s / 2.0)

    t_before = ts.from_datetime(dt_before)
    t_after  = ts.from_datetime(dt_after)
    t_center = ts.from_datetime(center_dt)

    d_before_Hz = _doppler_2way_for_time(t_before, earth, moon, station)
    d_after_Hz  = _doppler_2way_for_time(t_after, earth, moon, station)
    d_center_Hz = _doppler_2way_for_time(t_center, earth, moon, station)

    delta_doppler_Hz = d_after_Hz - d_before_Hz
    rate_Hz_per_s = delta_doppler_Hz / span_s
    rate_Hz_per_min = rate_Hz_per_s * 60.0

    return rate_Hz_per_s, rate_Hz_per_min, d_center_Hz

# ================== PLOTTING ==================

def plot_distance_and_doppler():
    hours, dist_km, Rdot_m_s, doppler_2way_Hz, moon_up = compute_eme_day()

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Distance on left axis
    ln1 = ax1.plot(hours, dist_km, label="Range Moon–station", color="tab:blue")
    ax1.set_xlabel("Time [hours UTC]")
    ax1.set_ylabel("Distance [km]", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.grid(True, which="both", linestyle="--", alpha=0.4)

    # Doppler on right axis
    ax2 = ax1.twinx()
    doppler_kHz = doppler_2way_Hz / 1e3
    ln2 = ax2.plot(hours, doppler_kHz, label="2-way Doppler", color="tab:red")
    ax2.set_ylabel(f"2-way Doppler @ {FREQ_HZ/1e6:.3f} MHz [kHz]", color="tab:red")
    ax2.tick_params(axis="y", labelcolor="tab:red")

    # Highlight when Moon is above horizon
    for i in range(len(hours) - 1):
        if moon_up[i]:
            ax1.axvspan(hours[i], hours[i+1], color="green", alpha=0.05)

    lines = ln1 + ln2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper right")

    fig.suptitle(
        f"EME geometry for {YEAR}-{MONTH:02d}-{DAY:02d} (lat={STATION_LAT}°, lon={STATION_LON}°)"
    )
    fig.tight_layout()
    plt.show()

def plot_distance_and_doppler_interval():
    # e.g. 1 hour, 1-minute steps
    hours, dist_km, Rdot_m_s, doppler_Hz, moon_up = compute_eme_interval(
        duration_hours=1/60,
        step_minutes=1
    )

    fig, ax1 = plt.subplots(figsize=(10, 5))

    ln1 = ax1.plot(hours * 60, dist_km, label="Range", color="tab:blue")
    ax1.set_xlabel("Time [minutes]")
    ax1.set_ylabel("Distance [km]", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.grid(True, linestyle="--", alpha=0.4)

    ax2 = ax1.twinx()
    ln2 = ax2.plot(hours * 60, doppler_Hz / 1e3, label="2-way Doppler", color="tab:red")
    ax2.set_ylabel(f"Doppler @ {FREQ_HZ/1e6:.3f} MHz [kHz]", color="tab:red")
    ax2.tick_params(axis="y", labelcolor="tab:red")

    lines = ln1 + ln2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper right")

    dist_diff_per_step_km = np.diff(dist_km)          # km per step
    dopp_diff_per_step_Hz = np.diff(doppler_Hz)       # Hz per step

    print(f"Typical distance change per minute: {np.mean(dist_diff_per_step_km):.2f} km/min")
    print(f"Typical Doppler change per minute : {np.mean(dopp_diff_per_step_Hz)/1e3:.2f} kHz/min")

    plt.tight_layout()
    plt.show()

def demo_rx_after_2_seconds():
    seconds, dist_km, Rdot_m_s, doppler_Hz, f_rx_Hz, moon_up = compute_eme_interval_seconds(
        duration_seconds=2.0,
        step_seconds=0.1
    )

    idx_2s = np.argmin(np.abs(seconds - 2.0))

    print(f"Time after TX     : {seconds[idx_2s]:.1f} s")
    print(f"2-way Doppler     : {doppler_Hz[idx_2s]:.2f} Hz")
    print(f"RX frequency echo : {f_rx_Hz[idx_2s] / 1e6:.9f} MHz")

# ================== MAIN ==================

if __name__ == "__main__":
    plot_distance_and_doppler()
    demo_rx_after_2_seconds()

    # Beispiel: Doppler-Änderung um 10:30 UTC
    rate_s, rate_min, d_center = doppler_change_at_utc(
        hour_utc=17,
        minute_utc=55,
        span_s=2.3
    )

    print("\n=== Doppler-Änderung  ===")
    print(f"Doppler  : {d_center/1e3:.3f} kHz")
    print(f"Änderungsrate          : {rate_s:.2f} Hz/s  ({rate_min:.2f} Hz/min)")
