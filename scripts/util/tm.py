import numpy as np
a=6378137.0; f=1/298.257222101; e2=f*(2-f); ep2=e2/(1-e2); k0=0.9996; lon0=np.radians(-9.0); FE=500000.0
e4=e2*e2; e6=e4*e2
def M(phi):
    return a*((1-e2/4-3*e4/64-5*e6/256)*phi-(3*e2/8+3*e4/32+45*e6/1024)*np.sin(2*phi)+(15*e4/256+45*e6/1024)*np.sin(4*phi)-(35*e6/3072)*np.sin(6*phi))
def fwd(lat,lon):
    phi=np.radians(lat); lam=np.radians(lon)
    N=a/np.sqrt(1-e2*np.sin(phi)**2); T=np.tan(phi)**2; C=ep2*np.cos(phi)**2; A=(lam-lon0)*np.cos(phi)
    x=FE+k0*N*(A+(1-T+C)*A**3/6+(5-18*T+T*T+72*C-58*ep2)*A**5/120)
    y=k0*(M(phi)+N*np.tan(phi)*(A*A/2+(5-T+9*C+4*C*C)*A**4/24+(61-58*T+T*T+600*C-330*ep2)*A**6/720))
    return x,y
def inv(x,y):
    m=y/k0; mu=m/(a*(1-e2/4-3*e4/64-5*e6/256)); e1=(1-np.sqrt(1-e2))/(1+np.sqrt(1-e2))
    p1=mu+(3*e1/2-27*e1**3/32)*np.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*np.sin(4*mu)+(151*e1**3/96)*np.sin(6*mu)+(1097*e1**4/512)*np.sin(8*mu)
    N1=a/np.sqrt(1-e2*np.sin(p1)**2); T1=np.tan(p1)**2; C1=ep2*np.cos(p1)**2; R1=a*(1-e2)/(1-e2*np.sin(p1)**2)**1.5; D=(x-FE)/(N1*k0)
    phi=p1-(N1*np.tan(p1)/R1)*(D*D/2-(5+3*T1+10*C1-4*C1*C1-9*ep2)*D**4/24+(61+90*T1+298*C1+45*T1*T1-252*ep2-3*C1*C1)*D**6/720)
    lam=lon0+(D-(1+2*T1+C1)*D**3/6+(5-2*C1+28*T1-3*C1*C1+8*ep2+24*T1*T1)*D**5/120)/np.cos(p1)
    return np.degrees(phi),np.degrees(lam)
