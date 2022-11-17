
DTED_LEN=1201
DTED_STEP=1/DTED_LEN

EXT_DTED0 =".dt0"
EXT_DTED1 =".dt1"
EXT_DTED2 =".dt2"



__DTED_FILE_PATH="./Input/N39E032.dt1"


import os
import re
from math import trunc
from struct import unpack
import numpy as np
from enum import Enum


class HeightQuery(Enum):
    INTERPOLATE = 0
    NEAREST = 1

#taken from https://github.com/phlay/srtm-dted/blob/master/srtm-dted.py

class ParseError(Exception): pass

# decode 16bit signed big-endian non-complemented as used
# as elevation data in DTED files.
# if x == 0xffff it is, acording to our spec, interpreted as invalid/unknown,
# and 'None' is returned instead of -32767. This should prevent using this
# number by accident in a calculation.
#
def decode_be16nc(x):
	if x == 0xffff:
		return None
	elif x >= 0x8000:
		return 0x8000-x
	return x

def bilinear_interpolation(x, y, points):
    '''Interpolate (x,y) from values associated with four points.

    The four points are a list of four triplets:  (x, y, value).
    The four points can be in any order.  They should form a rectangle.

        >>> bilinear_interpolation(12, 5.5,
        ...                        [(10, 4, 100),
        ...                         (20, 4, 200),
        ...                         (10, 6, 150),
        ...                         (20, 6, 300)])
        165.0

    '''
    # See formula at:  http://en.wikipedia.org/wiki/Bilinear_interpolation

    points = sorted(points)               # order points by x, then by y
    (x1, y1, q11), (_x1, y2, q12), (x2, _y1, q21), (_x2, _y2, q22) = points

    if x1 != _x1 or x2 != _x2 or y1 != _y1 or y2 != _y2:
        raise ValueError('points do not form a rectangle')
    if not x1 <= x <= x2 or not y1 <= y <= y2:
        raise ValueError('(x, y) not within the rectangle')

    return (q11 * (x2 - x) * (y2 - y) +
            q21 * (x - x1) * (y2 - y) +
            q12 * (x2 - x) * (y - y1) +
            q22 * (x - x1) * (y - y1)
           ) / ((x2 - x1) * (y2 - y1) + 0.0)

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

	def deci(self):
		x = self.hms
		erg = trunc(x)

		for i in range(2):
			erg *= 60
			x *= 100
			erg += trunc(x) % 100

		return erg / 3600


	#returns floating part
	#ex: 58.658 -> 0.658 
	def floating_part(self):
		return self.hms-trunc(self.hms)

	#returns subcoords ex: 58.658 -> 0.658 /(1/1201) = 822.5 -> returns 822.5
	def sub_coord(self):
		return self.floating_part()/DTED_STEP

		#old version
		#x0 = (trunc(100 * self.hms) % 100) % 15
		#x1 = trunc(10000 * self.hms) % 100

		#if self.hemi == 'N' or self.hemi == 'E':
		#	return 60*x0 + x1
		#else:
		#	return 900 - 60*x0 - x1

	
	#returns subcoords ex: 58.658 -> 0.658 /(1/1201) = 822.5 -> returns 0.5
	def sub_coord_floating(self):
		return self.sub_coord()-trunc(self.sub_coord())

	# give the name (-component) of the map this coordinate belongs to
	def mapname(self):
		x = trunc(self.hms * 100)

		if self.hemi == 'N' or self.hemi == 'E':
			x = ( x - ((x % 100) % 15) ) * 100
		else:
			x = ( x - ((x % 100) % 15) + 15 ) * 100

		if self.type == 'latitude':
			return self.hemi + '%06d' % x
		elif self.type == 'longitude':
			return self.hemi + '%07d' % x

class DTED:
	data = None
	mapname = None
	folder =None

	def __init__(self, folder):
		print(f'DTED reader initiated with {folder} directory')
		self.data = {}
		self.folder = folder
		
	def fix_invalid_dted_data(self,height_map):
    
		# Find invalid values in height_map
		height_map = np.ma.masked_array(height_map, height_map == None)
		before_count = np.ma.count_masked(height_map) # For debugging
		# Replace invalid values with close neighbors
		for shift in (-1,1):
			for axis in (1,0):        
				height_map_shifted = np.roll(height_map, shift=shift, axis=axis)
				idx = ~height_map_shifted.mask * height_map.mask
				height_map[idx] = height_map_shifted[idx]
		# Sometimes, even after running the code above doesn't fix the problem.
		# In that case, recursive calls may be necessary
		height_map = np.ma.masked_array(height_map, height_map == None)
		if np.ma.count_masked(height_map) > 0:
			height_map = self.fix_invalid_dted_data(height_map)
		after_count = np.ma.count_masked(height_map) # For debugging
		#print(f'{before_count - after_count} invalid DTED values are interpolated')

		return height_map

	def readfromfile(self, file):
		self.mapname = file			
		single_dted_data=[]

		with open(file, 'rb') as f:
			#
			# parse UHL header
			#

			# check magic and version
			if f.read(3) != b'UHL':
				raise ParseError('wrong magic')
			if f.read(1) != b'1':
				raise ParseError('wrong version')

			self.longitude = f.read(8).decode('utf-8')
			self.latitude = f.read(8).decode('utf-8')

			self.longival = int(f.read(4))/10
			self.latival = int(f.read(4))/10

			temp = f.read(4)
			if temp == b'NA  ':
				self.vacc = None
			else:
				self.vacc = int(temp)

			self.usc = f.read(3)
			self.uref = f.read(12)

			self.num_long = int(f.read(4))
			self.num_lat = int(f.read(4))

			self.mult_acc = int(f.read(1))

			self.reserved = f.read(24)

			#
			# skip other headers
			#
			f.seek(648, 1)		# DSI
			f.seek(2700, 1)		# ACC

			#
			# now go for the data blocks
			#
			for i in range(self.num_long):
				# check magic number of record
				if int(unpack('>B', f.read(1))[0]) != 0xaa:
					raise ParseError('wrong magic in data block')

				seq = unpack('>I', b'\x00' + f.read(3))[0]

				long_cnt = unpack('>H', f.read(2))[0]
				if long_cnt != i:
					raise ParseError('unexpected longitude number: ' + str(long_cnt))

				lat_cnt = unpack('>H', f.read(2))[0]
				if lat_cnt != 0:
					raise ParseError('latitude count not zero')

				# read elevations
				rowdata = f.read(2 * self.num_lat)

				#ERROR HERE!  TODO!
				#_________________________________________________________________________
				# check values with checksum
				# (checksum is calculated in regular 2-complement)
				checksum = unpack('>i', f.read(4))[0]				
				#rowsum = sum(unpack('>' + 901*'h', rowdata))
				rowsum = sum(unpack('>' + self.num_lat*'H', rowdata))

				#print(f"rowdata[]: {rowdata[3]}")

				#print(f"checksum: {checksum}, rowsum:{rowsum}")

				#if rowsum != checksum:
				#	raise ParseError(f'checksum failed on longitude {str(i) }., should be: { str(checksum) } but is { str(rowsum)}')
				#_________________________________________________________________________
				

				# add row to matrix, this time values are
				# interpreted as signed big endian 16it non-complement
				#single_dted_data.append(unpack('>' + self.num_lat * 'h', rowdata))
				single_dted_data.append([ decode_be16nc(x) for x in unpack('>' + self.num_lat * 'h', rowdata)][::-1])
			single_dted_data=list(map(list, zip(*single_dted_data)))


		invalid_dted_data_number=0
		for x in single_dted_data:
			if(x is None):
				invalid_dted_data_number+=1

		print(f"invalid dted number is: {invalid_dted_data_number}")
		
		return self.fix_invalid_dted_data(single_dted_data)


	def get_dted(self,coords,level=1,lat_round_up=False,lon_round_up=False):		
		lat,lon = get_lat_lon(coords)

		#print(f"lat.get_hms(): {lat.get_hms()}")
		#print(f"trunc(lat.get_hms()): {trunc(lat.get_hms())}")
		#print(f"round(lat.sub_coord()): {round(lat.sub_coord())}")
		#print(f"(round(lat.sub_coord())/DTED_LEN): {(round(lat.sub_coord())/DTED_LEN)}")
		#print(f"trunc(round(lat.sub_coord())/DTED_LEN): {trunc(round(lat.sub_coord())/DTED_LEN)}")

		
		if(lat_round_up):
			trunc_lat_name=lat.get_hemi()+str(trunc(lat.get_hms())+1).zfill(2)
		else:
			trunc_lat_name=lat.get_hemi()+str(trunc(lat.get_hms())).zfill(2)

		
		if(lon_round_up):
			trunc_lon_name=lon.get_hemi()+str(trunc(lon.get_hms())+1).zfill(3)
		else:
			trunc_lon_name=lon.get_hemi()+str(trunc(lon.get_hms())).zfill(3)

		desired_dted_file_name=(trunc_lat_name+trunc_lon_name+get_dted_extension_by_level(level))
		if(desired_dted_file_name not in self.data.keys()):
			self.data[desired_dted_file_name] = self.readfromfile(os.path.join(self.folder,desired_dted_file_name))

		#print(f"file name: {desired_dted_file_name}")

		return self.data[desired_dted_file_name]



	def get_dted_old(self,coords,level=1,lat_lower_bound=False,lon_lower_bound=False):		
		lat,lon = get_lat_lon(coords)

		print(f"lat.get_hms(): {lat.get_hms()}")
		print(f"trunc(lat.get_hms()): {trunc(lat.get_hms())}")
		print(f"round(lat.sub_coord()): {round(lat.sub_coord())}")
		print(f"(round(lat.sub_coord())/DTED_LEN): {(round(lat.sub_coord())/DTED_LEN)}")
		print(f"trunc(round(lat.sub_coord())/DTED_LEN): {trunc(round(lat.sub_coord())/DTED_LEN)}")

		if(lat_lower_bound):
			trunc_lat_name=lat.get_hemi()+str(trunc(lat.get_hms())).zfill(2)
		else:
			trunc_lat_name=lat.get_hemi()+str(trunc(lat.get_hms())+trunc(round(lat.sub_coord())/DTED_LEN)).zfill(2)

		#print(f"lat name: {trunc_lat_name}")

		#print(f"lon.get_hms(): {lon.get_hms()}")
		if(lon_lower_bound):
			trunc_lon_name=lon.get_hemi()+str(trunc(lon.get_hms())).zfill(3)
		else:
			trunc_lon_name=lon.get_hemi()+str(trunc(lon.get_hms())+trunc(round(lon.sub_coord())/DTED_LEN)).zfill(3)
		#print(f"lon name: {trunc_lon_name}")

		desired_dted_file_name=(trunc_lat_name+trunc_lon_name+get_dted_extension_by_level(level))
		if(desired_dted_file_name not in self.data.keys()):
			self.data[desired_dted_file_name] = self.readfromfile(os.path.join(self.folder,desired_dted_file_name))

		print(f"file name: {desired_dted_file_name}")

		return self.data[desired_dted_file_name]

	def get_dted_height_interpolated(self,coords,level=1):		

		dted_00= self.get_dted(coords,level,True,True)
		dted_01= self.get_dted(coords,level,True,False)
		dted_10= self.get_dted(coords,level,False,True)
		dted_11= self.get_dted(coords,level,False,False)
		
		lat,lon = get_lat_lon(coords)
		x0= trunc(lat.sub_coord())
		x1= (trunc(lat.sub_coord())+1) % DTED_LEN
		y0= trunc(lon.sub_coord())
		y1= (trunc(lon.sub_coord())+1) % DTED_LEN

		print("")
		print(f"interfolations: {lat.sub_coord_floating()}   {lon.sub_coord_floating()}")
		print(f"interpolation points: {dted_00[x0][y0]}  {dted_01[x0][y1]}")
		print(f"interpolation points: {dted_10[x1][y0]}  {dted_11[x1][y1]}")
		print("")
		
		points=(0, 0, dted_00[x0][y0]), (0, 1, dted_01[x0][y1]), (1, 0, dted_10[x1][y0]), (1, 1, dted_11[x1][y1])


		print(f"result: {bilinear_interpolation(lat.sub_coord_floating(),lon.sub_coord_floating(),points)}")
		print("")

		return bilinear_interpolation(lat.sub_coord_floating(),lon.sub_coord_floating(),points)

	def get_dted_height_nearest(self,coords,level=1):		
		desired_dted_data=self.get_dted(coords,level)
		lat,lon = get_lat_lon(coords)

		#print(f"lat.sub_coord(): {lat.sub_coord()}   rounded: {round(lat.sub_coord())}                  lon.sub_coord(): {lon.sub_coord()}     rounded: {round(lon.sub_coord())}  ")

		return desired_dted_data[round(lat.sub_coord())][round(lon.sub_coord())]
			
		
	def get_height(self,coords,level=1,height_query_type=HeightQuery.INTERPOLATE):
		return {
			HeightQuery.INTERPOLATE:	lambda coords,level: self.get_dted_height_interpolated(coords,level),
			HeightQuery.NEAREST:		lambda coords,level: self.get_dted_height_nearest(coords,level),
		}[height_query_type](coords,level)

	def get_height_map(self,bounds,resolution,scale,height_query_type=HeightQuery.INTERPOLATE):
		height_map=[]
		lat0,lon0 = get_lat_lon(bounds[0])		
		lat1,lon1 = get_lat_lon(bounds[1])

		#TODO E-W , S-N should be handled
		#print(f"lat from : {lat0.sub_coord()}    lat to:{lat0.sub_coord()+(DTED_LEN*(lat1.get_hms()-lat0.get_hms()))}  {lat1.get_hms()}-{lat0.get_hms()}  {DTED_LEN*(lat1.get_hms()-lat0.get_hms())}   iteration num: {resolution}")
		for lat in np.arange(lat0.sub_coord(),lat0.sub_coord()+(DTED_LEN*(lat1.get_hms()-lat0.get_hms())),resolution):
			for lon in np.arange(lon0.sub_coord(),lon0.sub_coord()+(DTED_LEN*(lon1.get_hms()-lon0.get_hms())),resolution):
				#print(f"lat: {lat}    lon:{lon}     iteration num: {resolution}")

				#print(f"(lon/DTED_LEN): {lon0.get_hms()} + {(lon/DTED_LEN)} = {trunc(lon0.get_hms())+(lon/DTED_LEN)}")

				lat_floating=trunc(lat/DTED_LEN)+(1-((lat/DTED_LEN)%1))
				lon_floating=(lon/DTED_LEN)

				lat_floating = lat_floating-(lat_floating%DTED_STEP)
				lon_floating = lon_floating-(lon_floating%DTED_STEP)


				c0=GeoCoord(lat0.get_hemi()+str(trunc(lat0.get_hms())+lat_floating))
				c1=GeoCoord(lon0.get_hemi()+str(trunc(lon0.get_hms())+lon_floating))
				coord=(c0,c1)

				#print(f"lat: {coord[0]}    lon:{coord[1]}")

				height = self.get_height(coord,1,height_query_type)
				height_map.append((lat*scale,lon*scale,height))


		return np.array(height_map)


def resolve_dted_file_path(file_path):
	dir_path = os.path.dirname(os.path.realpath(__file__))
	folder, file_name = os.path.split(file_path)
	file_name,file_extension = file_name.split(".")
	coord_pattern = re.compile("([A-Z][0-9]+)", re.I)
	coords = re.findall(coord_pattern, file_name)	

	return file_name,coords,file_extension

def resolve_dted_file_name(file_name):	
	file_name,file_extension = file_name.split(".")
	coord_pattern = re.compile("([A-Z][0-9]+)", re.I)
	coords = re.findall(coord_pattern, file_name)	

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

def get_dted_extension_by_level(level):
	    return {
        0: EXT_DTED0,
        1: EXT_DTED1,
        2: EXT_DTED2,
    }[level]
