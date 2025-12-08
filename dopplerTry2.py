import numpy as np
import matplotlib.pyplot as plt
from skyfield.api import load, wgs84

# ================== CONFIG ==================

STATION_LAT = 47.2237270     # deg
STATION_LON = 8.8176838      # deg
STATION_ELV = 466.63         # meters

# RF frequency
FREQ_HZ = 1296e6

# Day to simulate (UTC)
YEAR  = 2025
MONTH = 12
DAY   = 8

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
    eph = load('de421.bsp')
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
    eph = load('de421.bsp')
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
    # Create little vertical stripes where moon_up is True
    for i in range(len(hours) - 1):
        if moon_up[i]:
            ax1.axvspan(hours[i], hours[i+1], color="green", alpha=0.05)

    # Combined legend
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

    # if step_minutes = 1
    print(f"Typical distance change per minute: {np.mean(dist_diff_per_step_km):.2f} km/min")
    print(f"Typical Doppler change per minute : {np.mean(dopp_diff_per_step_Hz)/1e3:.2f} kHz/min")

    plt.tight_layout()
    plt.show()

# ================== MAIN ==================

if __name__ == "__main__":
    plot_distance_and_doppler()
