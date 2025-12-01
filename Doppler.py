import numpy as np
import ephem 
import datetime
from CalcMoonPos import get_observer

ftx = 1.296e9
c = 299792458 #m/s
#https://www.ok2kkw.com/00003016/eme2014/pdf/k2uyh_doppler_eme2014.pdf



def moon_dist(obs):
    moon = ephem.Moon(obs)
    moon.compute(obs)
    return float(moon.earth_distance) * ephem.meters_per_au

def moon_vel(obs, delta_s = 2.304):
    d = moon_dist(obs)

    obs2 = ephem.Observer()
    obs2.lat = obs.lat    
    obs2.lon = obs.lon    
    obs2.elevation = obs.elevation   
    obs2.date = ephem.now() + ephem.second * delta_s

    d2 = moon_dist(obs2)

    return (d2-d) / delta_s

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

    v = moon_vel(obs, 10)

    frx = doppler(1296000000, v)

    print(frx)