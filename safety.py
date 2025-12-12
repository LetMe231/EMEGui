import numpy as np

c = 299792458 #m/s
f = 1.296e9

r = 3 #m
E_dBuV_m = 70 #dBuV/m**2
E = 10**(E_dBuV_m/20)*1e-6
Z0 = 377 #Ohm

S = E**2 / Z0

A = 4 * np.pi * r**2

EIRPmax = S * A * 1000


# print(EIRPmax) #-55dbW max
# print(10*np.log10(EIRPmax))

G = 10*np.log10((1.795**2*np.pi**2)/(c/f)**2)
print(G)