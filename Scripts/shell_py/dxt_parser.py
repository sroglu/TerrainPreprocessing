from math import trunc
import os
import sys
#print(sys.executable)
from wand import image

#SCRIPTS_PATH = "D:\Assets\Blender\Projects\scripts"
#DXT_FOLDER_PATH = os.path.join(SCRIPTS_PATH,"resources","DXT")
#DXT_FOLDER_PATH = "C:\Project\aircraftvr\Data\TerrainTexture"
DXT_FOLDER_PATH = os.path.join('C:','Project','aircraftvr','Data','TerrainTexture')
DXT_NAME = "36_2_32_2.dxt1"


BIN_OUT_EXTENTION = 'timg'

ZOOM_LEVEL_FOLDERS= {
	11 : '11',
	13 : '13',
	16 : '16',
}

ZOOM_LEVEL_RESOLUTIONS= {
	11 : 1024,
	13 : 4096,
	16 : 16384,
}
ZOOM_LEVEL_DIVISIONS= {
	11 : 2,
	13 : 8,
	16 : 32,
}
ZOOM_LEVEL_DIVISIONS_HEX= {
	11 : 0x02,
	13 : 0x08,
	16 : 0x20,
}

PIXEL_FORMAT = {
	0 : 'dxt1',
	1 : 'dxt3',
	2 : 'dxt5',
	4 : 'ARGB',
	8 : 'Unknown'
}

def get_coords_from_filename(dxt_file):
	
	file_name,file_extension = dxt_file.split(".")
	lat , x , lon, y = file_name.split("_")
	return lat , lon, x , y


class DXT_Parser:
	def __init__(self, folder_name,pixel_format_number,zoom_level):
		pixel_format=PIXEL_FORMAT[pixel_format_number]
		zoom_level_folder=ZOOM_LEVEL_FOLDERS[zoom_level]
		zoom_level_resolution=ZOOM_LEVEL_RESOLUTIONS[zoom_level]
		division = ZOOM_LEVEL_DIVISIONS[zoom_level]
		
		if os.path.exists(folder_name):
			out_folder_root = os.path.join(folder_name, '_Results')

			
			dxt_folder = os.path.join(folder_name,zoom_level_folder)

			if os.path.exists(dxt_folder):
				dxt_files = os.listdir(dxt_folder)
				dxt_files = [dxt_file for dxt_file in dxt_files if dxt_file.endswith('.'+pixel_format)]				
				out_folder = os.path.join(out_folder_root, zoom_level_folder)
				dxt_temp=os.path.join(out_folder,"temp."+pixel_format)

				if not os.path.exists(out_folder):
					os.makedirs(out_folder)

				counter =0
				for dxt_file in dxt_files:
					counter+=1
					progress=counter/len(dxt_files)*100
					print('Converting dxt files... [%d%%]\r'%progress, end="")

					lat, lon, part_x, part_y = get_coords_from_filename(dxt_file)
					dxt_file_path = os.path.join(dxt_folder,dxt_file)
					out_dxt_file_path = os.path.join(out_folder,lat+'_'+part_x+'_'+lon+'_'+part_y+'.'+BIN_OUT_EXTENTION)

					with image.Image(filename =dxt_file_path) as img:
						img.compression = pixel_format
						img.resize(zoom_level_resolution,zoom_level_resolution)
						imagedata=[]
						imagedata.append(ZOOM_LEVEL_DIVISIONS_HEX[zoom_level])

						for y in range(division):
							for x in range(division):

								pixels = trunc(zoom_level_resolution/division)
								with img[(x*pixels):((x+1)*pixels), (y*pixels):((y+1)*pixels)] as chunk:
									chunk.compression = pixel_format
									chunk.alpha_channel = False									
									chunk.save(filename=dxt_temp)

									with open(dxt_temp, 'rb') as dxt_mini:
										head = bytearray(dxt_mini.read(128))
										data = dxt_mini.read(trunc(pixels*pixels/2))#there is 2 pixel info in 1 byte
										imagedata+=data

						with open(out_dxt_file_path, 'wb') as wf:
							wf.write(bytes(imagedata))							
							wf.close()
				os.remove(dxt_temp)
			else:
				print(f'DXT directory {dxt_folder} cannot be found. Please try again.')
				return

		else:
			print(f'DXT directory {folder_name} cannot be found. Please try again.')
			return



def get_key_from_dict(dict,val):
    for key, value in dict.items():
         if val == value:
             return key

#dxt_parser = DXT_Parser(DXT_FOLDER_PATH,0,11)
dxt_parser = DXT_Parser(sys.argv[1],get_key_from_dict(PIXEL_FORMAT,sys.argv[2]),int(sys.argv[3]))