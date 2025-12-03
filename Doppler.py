import numpy as np
import ephem 
import datetime
from CalcMoonPos import get_observer, get_moon_position

ftx = 1.296e9
c = 299792458 #m/s
#https://www.ok2kkw.com/00003016/eme2014/pdf/k2uyh_doppler_eme2014.pdf



def moon_dist(obs):
    r = 6367127
    moon = ephem.Moon(obs)
    moon.compute(obs)
    az, el = get_moon_position()
    alpha = 90 - el
    center_dist = float(moon.earth_distance) * ephem.meters_per_au

    d = np.sqrt(r**2 + center_dist**2 - 2*r*center_dist*np.cos(alpha))
    print(d)
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
    return ((v_rel/c)*f_tx)/np.sqrt(1-(v_rel**2/c**2))

def doppler_fitting(samp, f_doppler, Fs=20000):
    n = np.arange(len(samp))
    f_corr = np.exp(-2j*np.pi*f_doppler*(n/Fs))
    return samp * f_corr

if __name__ == "__main__":
    ftx = 1296000000
    c = 299792458 #m/s  

    obs = get_observer()

    v ,vdt= moon_vel(obs, 10)

    frx = doppler(1296000000, v)

    print(vdt)