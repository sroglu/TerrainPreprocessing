
DTED_LEN=1201
DTED_STEP=1/DTED_LEN



__DTED_FILE_PATH="./Input/N39E032.dt1"

import os
import re
from math import trunc
from struct import unpack


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
		
	def __str__(self):
		return str(self.hms) + self.hemi

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

	def __init__(self, file):
		self.data = []
		self.fromfile(file)

	def fromfile(self, file):
		self.mapname = file	

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
				#self.data.append([ decode_be16nc(x) for x in unpack('>' + self.num_lat * 'h', rowdata)])
				self.data.append([ decode_be16nc(x) for x in unpack('>' + self.num_lat * 'h', rowdata)][::-1])
			#self.data[::-1]
			self.data=list(map(list, zip(*self.data)))


def get_dted_height_interpolated(dted,coords):
	c0, c1 = coords

	if c0.type == 'latitude' and c1.type == 'longitude':
		lat, lon = c0, c1
	elif c0.type == 'longitude' and c1.type == 'latitude':
		lat, lon = c1, c0
	else:		
		raise Exception('you need longitude and latitude')


	x1= trunc(lat.sub_coord())
	x2= trunc(lat.sub_coord())+1
	y1= trunc(lon.sub_coord())
	y2= trunc(lon.sub_coord())+1
	points=(0, 0, dted.data[x1][y1]), (0, 1, dted.data[x1][y2]), (1, 0, dted.data[x2][y1]), (1, 1, dted.data[x2][y2])

	#print(f"lat.sub_coord(): {lat.sub_coord()}		lon.sub_coord(): {lon.sub_coord()}")
	#print(f"lat.sub_coord_floating(): {lat.sub_coord_floating()}    lon.sub_coord_floating(): {lon.sub_coord_floating()}")

	#print(f"    {dted.data[x1][y1]}----------------------------{dted.data[x1][y2]}")
	#print( "       |                            |       ")
	#print( "       |                            |       ")
	#print( "       |                            |       ")
	#print( "       |                            |       ")
	#print(f"    {dted.data[x2][y1]}----------------------------{dted.data[x2][y2]}")	

	return bilinear_interpolation(lat.sub_coord_floating(),lon.sub_coord_floating(),points)

def get_dted_height_nearest(dted,coords):
	c0, c1 = coords

	if c0.type == 'latitude' and c1.type == 'longitude':
		lat, lon = c0, c1
	elif c0.type == 'longitude' and c1.type == 'latitude':
		lat, lon = c1, c0
	else:		
		raise Exception('you need longitude and latitude')


	return dted.data[round(lat.sub_coord())][round(lon.sub_coord())]



	#print(f"lat.sub_coord(): {lat.sub_coord()}    lon.sub_coord(): {lon.sub_coord()}")

	#print(f"    {dted.data[x1][y1]}----------------------------{dted.data[x1][y2]}")
	#print( "       |                            |       ")
	#print( "       |                            |       ")
	#print( "       |                            |       ")
	#print( "       |                            |       ")
	#print(f"    {dted.data[x2][y1]}----------------------------{dted.data[x2][y2]}")	

	return bilinear_interpolation(lat.sub_coord(),lon.sub_coord(),points)

	#return dted.data[long.sub_coord()][lat.sub_coord()]

def resolve_dted_file(file_path):
	dir_path = os.path.dirname(os.path.realpath(__file__))
	folder, file_name = os.path.split(file_path)
	file_name,file_extension = file_name.split(".")
	coord_pattern = re.compile("([A-Z][0-9]+)", re.I)
	coords = re.findall(coord_pattern, file_name)	

	return file_name,file_extension,coords

def __read_dted_file_for_testing(file_path):
	folder, file_name = os.path.split(file_path)
	file_name,file_extension = file_name.split(".")
	coord_pattern = re.compile("([A-Z][0-9]+)", re.I)
	c0,c1 = re.findall(coord_pattern, file_name)

	print(f"{c0} {c1}")

	c0=f"{c0}.263"
	c1=f"{c1}.537"
	
	print(f"{c0} {c1}")


	lat=GeoCoord(c0)
	long=GeoCoord(c1)


	dted = DTED(file_path)

	#print(f"dted data at {lat.sub_coord()}, {long.sub_coord()} = {dted.data[long.sub_coord()][lat.sub_coord()]}")
	
	#print(dted.data)


#__read_dted_file_for_testing(__DTED_FILE_PATH)


dted = DTED(__DTED_FILE_PATH)
#Tests____________________________________________________________________________________
#c0="N39.263"
#c1="E32.537"

#lat=GeoCoord(c0)
#lon=GeoCoord(c1)

#print("")
#print(get_dted_height_interpolated(dted,(lat,lon)))
#print(get_dted_height_nearest(dted,(lat,lon)))


#print("")
#print("________________________________________________________________________________________")
#print("")


#c0="N39.653"
#c1="E32.794"

#lat=GeoCoord(c0)
#lon=GeoCoord(c1)

#print("")
#print(get_dted_height_interpolated(dted,(lat,lon)))
#print(get_dted_height_nearest(dted,(lat,lon)))


#print("")
#print("________________________________________________________________________________________")
#print("")


#c0="N39.124"
#c1="E32.325"

#lat=GeoCoord(c0)
#lon=GeoCoord(c1)

#print("")
#print(get_dted_height_interpolated(dted,(lat,lon)))
#print(get_dted_height_nearest(dted,(lat,lon)))
#_______________________________________________________________________________________________