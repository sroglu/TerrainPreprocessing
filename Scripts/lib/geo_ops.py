import math
import numpy as np
import re
from math import trunc

DTED_LEN=1201
DTED_STEP=1/DTED_LEN

DEG_2_RAD = (math.pi / 180)
EARTH_RADIUS = 6378137  # in meters
E2 = 0.0066943799901413165 # FLATTENING * (2-FLATTENING)

WGS84_a = 6378137.0
WGS84_b = 6356752.3142

#WGS84 manual calculated (less accurate)
WGS84_e2=(math.pow(WGS84_a,2)-math.pow(WGS84_b,2))/math.pow(WGS84_a,2)


def lla2ecef(lat, lon, altitude):

    lat_rad = lat * DEG_2_RAD
    lon_rad = lon * DEG_2_RAD

    sinphi = math.sin(lat_rad)
    cosphi = math.cos(lat_rad)

    N = EARTH_RADIUS / (1 - E2 * sinphi ** 2) ** 0.5
    rho = (N + altitude) * cosphi

    z = (N * (1 - E2) + altitude) * sinphi
    x = rho * math.cos(lon_rad)
    y = rho * math.sin(lon_rad)

    on_earth_pos = np.array([x, y, z])

    return on_earth_pos

def degree_length_of_longitude(lat):
	return (DEG_2_RAD*WGS84_a*math.cos(lat*DEG_2_RAD))/math.sqrt(1-(E2*math.pow(math.sin(lat*DEG_2_RAD),2)))

def degree_length_of_latitude(lon):
	return 111132.954-559.822*math.cos(2*lon)+1.175*math.cos(4*lon)
	return (DEG_2_RAD*WGS84_a*math.cos(lat*DEG_2_RAD))/math.sqrt(1-(E2*math.pow(math.sin(lat*DEG_2_RAD),2)))

def translate_to_geo_rot(lat, lon):
    return (0,-lon,lat)


class GeoCoord:
	type = None

	# hemi is either 'N' or 'S' for type=='latitude'
	# or 'E' / 'W' for type == 'longitude'
	hemi = None

	# numerical coordinate in hms
	hms = None

	def __init__(self, str):
		self.from_str(str)

	# format: D.MMSSH
	# where H is the hemisphere
	# for example: 47.2516N
	# for 47 deg 25 min and 16 sec northern hemisphere
	def from_str(self, str):
		H = str[0].upper()

		if H == 'N' or H == 'S':
			self.hemi = H
			self.type = 'latitude'
		elif H == 'W' or H == 'E':
			self.hemi = H
			self.type = 'longitude'			

		self.hms = float(str[1:])
		
	def get_hms(self):
		return self.hms	

	def get_hemi(self):
		return self.hemi

	def __str__(self):
		return self.hemi+str(self.hms)

	#returns floating part
	#ex: 58.658 -> 0.658 
	def floating_part(self):
		return self.hms-trunc(self.hms)

	#returns subcoords ex: 58.658 -> 0.658 /(1/1201) = 822.5 -> returns 822.5
	def dted_sub_coord(self):
		return self.floating_part()/DTED_STEP
	
	#returns subcoords ex: 58.658 -> 0.658 /(1/1201) = 822.5 -> returns 0.5
	def sub_coord_floating(self):
		return self.sub_coord()-trunc(self.sub_coord())


def resolve_coord_name(coord_name):	
	coord_name,file_extension = coord_name.split(".")
	coord_pattern = re.compile("([A-Z][0-9]+)", re.I)
	coords = re.findall(coord_pattern, coord_name)	

	return coords,file_extension

def get_lat_lon(coords):
	c0, c1 = coords
	if c0.type == 'latitude' and c1.type == 'longitude':
		lat, lon = c0, c1
	elif c0.type == 'longitude' and c1.type == 'latitude':
		lat, lon = c1, c0
	else:		
		raise Exception('you need longitude and latitude')
	return lat,lon

class GeoLocation:
	c1=None
	c2=None
	lat=None
	lon=None
	lat_trunc=None
	lon_trunc=None
	geo_coord_lat=None
	geo_coord_lon=None
	coords = None

	def __str__(self):
		return self.geo_coord_lat.__str__()+" - "+self.geo_coord_lon.__str__()

	def file_name(self):
		return self.geo_coord_lat.get_hemi()+str(trunc(self.geo_coord_lat.get_hms())).zfill(2) + self.geo_coord_lon.get_hemi()+str(trunc(self.geo_coord_lon.get_hms())).zfill(3)
	
	def __init__(self, coord_str):
		self.c1,self.c2= resolve_coord_name(coord_str)[0]
		self.geo_coord_lat,self.geo_coord_lon = get_lat_lon((GeoCoord(self.c1),GeoCoord(self.c2)))
		self.lat = self.geo_coord_lat.get_hms()
		self.lon = self.geo_coord_lon.get_hms()
		self.lat_trunc=trunc(self.lat)
		self.lon_trunc=trunc(self.lon)

		self.coords = (self.geo_coord_lat,self.geo_coord_lon)


