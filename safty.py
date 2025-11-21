import numpy as np

r = 3 #m
E_dBuV_m = 70 #dBuV/m**2
E = 10**(E_dBuV_m/20)*1e-6
Z0 = 377 #Ohm

S = E**2 / Z0

A = 4 * np.pi * r**2

EIRPmax = S * A


print(EIRPmax)