import numpy as np

c = 299792458 #m/s
f = 1.296e9

P = 10*np.log10(50000)
N0 = -174

L1 = 1.5 + 1.95 + 0.14 #alle 3 Kabel von antenne bis LNA + Limiter (5fuss & 7.5m angenommen)
L2 = 3.9 + 1.2 #beide Kabel von LNA bis usrp (15m und 4fuss)

Flna = 10**(0.46/10) # NF to F von LNA
Glna = 15
Fusrp = 10**(8/10) # NF to F von usrp

F = L1 + (Flna - 1)*L1 + ((L2 - 1)*L1)/Glna + ((Fusrp - 1)*L1*L2)/Glna
NF = 10*np.log10(F)

# F2 = Flna + (L1 -1)/Glna + ((L2 -1)*L1)/Glna + ((Fusrp -1)*L1*L2)/Glna
# NF2 = 10*np.log10(F2)

Loneway = -147.6 + 20*np.log10(363104000) + 20*np.log10(f)

#https://hamradio.engineering/eme-path-loss-free-space-loss-passive-reflector-loss/
r2 = 1737400**2
EffA = 0.7*(2*np.pi*r2) #70% of Moons aperture are considered usefull
MoonG = 10*np.log10((4*np.pi*EffA)/(c/f)**2)
refcoeff = 0.065
refL = 10*np.log10(refcoeff)

Lp = 2 * Loneway - refL

GainAnt = 26
B = 10*np.log10(40)
SNR = 0
P0 = N0 + B + NF + SNR + Lp - 2*GainAnt - MoonG

print(P0)