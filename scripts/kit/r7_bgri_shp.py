"""Converte bgri2021_corredor.geojson (EPSG 3763, PT-TM06) para shapefile em EPSG 25829, sem GDAL."""
import json, struct, numpy as np, sys
sys.path.insert(0, '.')
from tm import fwd
a=6378137.0; f=1/298.257222101; e2=f*(2-f); ep2=e2/(1-e2); e4=e2*e2; e6=e4*e2
def Mf(phi): return a*((1-e2/4-3*e4/64-5*e6/256)*phi-(3*e2/8+3*e4/32+45*e6/1024)*np.sin(2*phi)+(15*e4/256+45*e6/1024)*np.sin(4*phi)-(35*e6/3072)*np.sin(6*phi))
lat0=np.radians(39.66825833333333); lon0=np.radians(-8.133108333333334); k0=1.0
def inv_tm06(x,y):
    m=Mf(lat0)+y/k0; mu=m/(a*(1-e2/4-3*e4/64-5*e6/256)); e1=(1-np.sqrt(1-e2))/(1+np.sqrt(1-e2))
    p1=mu+(3*e1/2-27*e1**3/32)*np.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*np.sin(4*mu)+(151*e1**3/96)*np.sin(6*mu)+(1097*e1**4/512)*np.sin(8*mu)
    N1=a/np.sqrt(1-e2*np.sin(p1)**2); T1=np.tan(p1)**2; C1=ep2*np.cos(p1)**2; R1=a*(1-e2)/(1-e2*np.sin(p1)**2)**1.5; D=x/(N1*k0)
    phi=p1-(N1*np.tan(p1)/R1)*(D*D/2-(5+3*T1+10*C1-4*C1*C1-9*ep2)*D**4/24+(61+90*T1+298*C1+45*T1*T1-252*ep2-3*C1*C1)*D**6/720)
    lam=lon0+(D-(1+2*T1+C1)*D**3/6+(5-2*C1+28*T1-3*C1*C1+8*ep2+24*T1*T1)*D**5/120)/np.cos(p1)
    return np.degrees(phi),np.degrees(lam)
def conv(ring):
    r=np.asarray(ring,float); la,lo=inv_tm06(r[:,0],r[:,1]); x,y=fwd(la,lo); return np.c_[x,y]
def area(r): return 0.5*np.sum(r[:-1,0]*r[1:,1]-r[1:,0]*r[:-1,1])
d=json.load(open(sys.argv[1]))
recs=[]
for ft in d['features']:
    g=ft['geometry']; polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    parts=[]
    for poly in polys:
        for k,ring in enumerate(poly):
            r=conv(ring)
            if k==0 and area(r)>0: r=r[::-1]      # exterior: sentido horário (shapefile)
            if k>0 and area(r)<0: r=r[::-1]       # buracos: anti-horário
            parts.append(r)
    recs.append((ft['properties'],parts))
# --- escrever shapefile
def bbox(pts): return pts[:,0].min(),pts[:,1].min(),pts[:,0].max(),pts[:,1].max()
shp=bytearray(); shx=bytearray(); off=50
allp=np.vstack([np.vstack(p) for _,p in recs]); BB=bbox(allp)
for i,(pr,parts) in enumerate(recs):
    pts=np.vstack(parts); nparts=len(parts); npts=len(pts)
    content=struct.pack('<i',5)+struct.pack('<4d',*bbox(pts))+struct.pack('<2i',nparts,npts)
    idx=0
    for p in parts: content+=struct.pack('<i',idx); idx+=len(p)
    content+=pts.astype('<f8').tobytes()
    clen=len(content)//2
    shx+=struct.pack('>2i',off,clen); shp+=struct.pack('>2i',i+1,clen)+content; off+=4+clen
def header(length):
    return struct.pack('>7i',9994,0,0,0,0,0,length)+struct.pack('<2i',1000,5)+struct.pack('<4d',*BB)+struct.pack('<4d',0,0,0,0)
open('bgri/bgri2021_corredor_25829.shp','wb').write(header(50+len(shp)//2)+shp)
open('bgri/bgri2021_corredor_25829.shx','wb').write(header(50+len(shx)//2)+shx)
# dbf
fields=[('BGRI2021',11),('DTMN21',4),('DTMNFR21',6)]
n=len(recs); hl=32+32*len(fields)+1; rl=1+sum(w for _,w in fields)
dbf=bytearray(struct.pack('<BBBBIHH20x',3,126,11,22,n,hl,rl))
for nm,w in fields: dbf+=nm.encode().ljust(11,b'\0')+b'C'+b'\0'*4+bytes([w,0])+b'\0'*14
dbf+=b'\r'
for pr,_ in recs:
    dbf+=b' '+b''.join(str(pr[nm]).encode().ljust(w)[:w] for nm,w in fields)
dbf+=b'\x1a'; open('bgri/bgri2021_corredor_25829.dbf','wb').write(dbf)
open('bgri/bgri2021_corredor_25829.prj','w').write(open('/mnt/user-data/uploads/rotura-alqueva_orig/hecras/Terrain/Terreno_SRTM.vrt').read().split('<SRS dataAxisToSRSAxisMapping="1,2">')[1].split('</SRS>')[0])
print('registos',n,'pontos',len(allp),'bbox',[round(v) for v in BB])
