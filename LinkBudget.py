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
r = 1737400
EffA = 0.7*(np.pi*r**2) #70% of Moons aperture are considered usefull
MoonG = 10*np.log10(4*np.pi) + 10* np.log10(EffA) + 20*np.log10(f) - 20*np.log10(c)
refcoeff = 0.065
refL = 10*np.log10(refcoeff)

GainAnt = 26
Prx = (((c/f)**2)/(4*np.pi)**3) * GainAnt**2 * (50/r**4) * EffA

Lp = 10*np.log10((4*np.pi)**3) + 40*np.log10(r) + 20*np.log10(f) - 20*np.log10(c) - 10*np.log10(EffA) # S342 Eq. 10.4 PTx * G * G * Lp = PRx

B = 10*np.log10(40)
SNR = 0
P0 = N0 + B + NF + SNR + Lp - 2*GainAnt

print(P0)