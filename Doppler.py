
import numpy as np
import matplotlib.pyplot as plt
import ephem
import math 
import pyTMD.astro
import datetime
from CalcMoonPos import get_observer, get_moon_position

ftx = 1.296e9
c = 299792458 #m/s
#https://www.ok2kkw.com/00003016/eme2014/pdf/k2uyh_doppler_eme2014.pdf

# def llh_to_ecef(lat_deg, lon_deg, h_m):
#     """
#     WGS-84: geodätische Koordinaten (lat, lon, h) -> ECEF (x, y, z)

#     lat_deg: Breite in Grad (+N, -S)
#     lon_deg: Länge in Grad (+E, -W)
#     h_m: Höhe in Metern über WGS-84-Ellipsoid
#     """
#     # WGS-84 Parameter
#     a = 6378137.0               # Halbe große Achse [m]
#     e2 = 6.69437999014e-3       # Exzentrizität^2

#     # Grad -> Radiant
#     lat = math.radians(lat_deg)
#     lon = math.radians(lon_deg)

#     sin_lat = math.sin(lat)
#     cos_lat = math.cos(lat)
#     cos_lon = math.cos(lon)
#     sin_lon = math.sin(lon)

#     # Radius der Krümmung in der Vertikalen
#     N = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)

#     # ECEF
#     x = (N + h_m) * cos_lat * cos_lon
#     y = (N + h_m) * cos_lat * sin_lon
#     z = (N * (1.0 - e2) + h_m) * sin_lat

#     return np.array([x, y, z])

def moon_dist(obs):
    r = 6367127
    moon = ephem.Moon(obs)
    moon.compute(obs)
    az, el = get_moon_position()
    alpha = 90 - el
    center_dist = float(moon.earth_distance) * ephem.meters_per_au

    d = np.sqrt(r**2 + center_dist**2 - 2*r*center_dist*np.cos(alpha))
    return d

def moon_vel(obs, delta_s = 2.304):
    d = moon_dist(obs)

    obs2 = ephem.Observer()
    obs2.lat = obs.lat    
    obs2.lon = obs.lon    
    obs2.elevation = obs.elevation   
    obs2.date = ephem.now() + ephem.second * delta_s

    d2 = moon_dist(obs2)
    v = (d2-d) / delta_s

    obs3 = ephem.Observer()
    obs3.lat = obs.lat    
    obs3.lon = obs.lon    
    obs3.elevation = obs.elevation   
    obs3.date = ephem.now() + ephem.second * 2

    d3 = moon_dist(obs3)

    obs4 = ephem.Observer()
    obs4.lat = obs.lat    
    obs4.lon = obs.lon    
    obs4.elevation = obs.elevation   
    obs4.date = ephem.now() + ephem.second * (2+delta_s)

    d4 = moon_dist(obs4)

    v2 = (d4-d3) / delta_s

    vdt = (v2-v) / 2

    return v, vdt

def doppler(f_tx, v_rel):
    c = 299792458 #m/s
    return #((v_rel/c)*f_tx)/np.sqrt(1-(v_rel**2/c**2))

def doppler_fitting(samp, f_doppler, Fs=20000):
    n = np.arange(len(samp))
    f_corr = np.exp(-2j*np.pi*f_doppler*(n/Fs))
    return samp * f_corr

if __name__ == "__main__":
    ftx = 1296000000
    c = 299792458 #m/s

    obs = get_observer()

    # [x, y, z] = llh_to_ecef(obs.lat, obs.lon, obs.elevation)
    # moon_ECEF = pyTMD.astro.lunar_approximate(61017)
    # moon_ECEF = np.array(moon_ECEF).flatten()   

    t = np.arange(0, 61)
    dist_vec = []
    # dist_ECEF_vec = []
    v_vec = []
    vdt_vec = []
    doppler_vec = []

    for x in t:

        obsn = ephem.Observer()
        obsn.lat = obs.lat    
        obsn.lon = obs.lon    
        obsn.elevation = obs.elevation   
        obsn.date = ephem.now() + ephem.second * x

        # me_ECEF = llh_to_ecef(obsn.lat, obsn.lon, obsn.elevation)
        # d2 = moon_ECEF - me_ECEF
        # dist_ECEF_vec.append(np.linalg.norm(d2))

        d = moon_dist(obsn)
        v, vdt = moon_vel(obsn)
        f = doppler(ftx, moon_vel(obsn)[0])

        dist_vec.append(d)
        v_vec.append(v)
        vdt_vec.append(vdt)
        doppler_vec.append(f)

    fig, ax = plt.subplots(clear=True, constrained_layout=True)
    ax.set_ylabel('distance in m')
    ax.plot(t, dist_vec)
    # fig, ax = plt.subplots(clear=True, constrained_layout=True)
    # ax.set_ylabel('distance in m, ECEF')
    # ax.plot(t, dist_ECEF_vec)
    fig, ax = plt.subplots(clear=True, constrained_layout=True)
    ax.set_ylabel('velocity in m/s')
    ax.plot(t, v_vec)
    fig, ax = plt.subplots(clear=True, constrained_layout=True)
    ax.set_ylabel('accel in m/s^2')
    ax.plot(t, vdt_vec)
    fig, ax = plt.subplots(clear=True, constrained_layout=True)
    ax.set_ylabel('doppler in Hz')
    ax.plot(t, doppler_vec)
    plt.show()

    v ,vdt= moon_vel(obs, 10)

    frx = doppler(1296000000, v)

    print(frx)