import math
import struct
import numpy as np
import time
from osgeo import gdal


DTED_FILE_PATH = os.path.join(PROJECT_DIR,"Resources","DTED","N39E032.dt1")
DTED_FOLDER_PATH = os.path.join(PROJECT_DIR,"Resources","DTED")


def read_dted_using_gdal(file_path):    

    # Read file with GDAL
    src_ds = gdal.Open(file_path)
    # Get height map
    height_map = src_ds.ReadAsArray()

    #print(height_map)
    return height_map



##initiate reader with folder name and dted level(opt.)
#dted_reader=dted_ops.DTED(DTED_FOLDER_PATH)

##Create geocoords 
##coords,file_extension=resolve_dted_file_name("N39E032.dt1")
#c0="N39.263"
#c1="E32.537"

#lat=dted_ops.GeoCoord(c0)
#lon=dted_ops.GeoCoord(c1)

##get interpolated or nearest dted height
#coords =(lat,lon)
#desired_height_interpolated = dted_reader.get_dted_height_interpolated(coords)
#desired_height_nearest = dted_reader.get_dted_height_nearest(coords)

#print(f"interpolated height at coords {str(lat)},{str(lon)}:  {desired_height_interpolated}")
#print(f"nearest height at coords {str(lat)},{str(lon)}:  {desired_height_nearest}")



c0="N39"
c1="E32"
lat=dted_ops.GeoCoord(c0)
lon=dted_ops.GeoCoord(c1)
coords =(lat,lon)
dted_reader=dted_ops.DTED(DTED_FOLDER_PATH)
custom_reader_data=dted_reader.get_dted(coords)




c0="N39"
c1="E32"
lat=dted_ops.GeoCoord(c0)
lon=dted_ops.GeoCoord(c1)
coords =(lat,lon)

print(f"dted_reader height: {dted_reader.get_height(coords,1,dted_ops.HeightQuery.INTERPOLATE)}     {custom_reader_data[0][0]}")




c0="N39"
c1="E32.99958368026644"
lat=dted_ops.GeoCoord(c0)
lon=dted_ops.GeoCoord(c1)
coords =(lat,lon)

print(f"dted_reader height: {dted_reader.get_height(coords,1,dted_ops.HeightQuery.INTERPOLATE)}     {custom_reader_data[0][1200]}")



c0="N39.99958368026644"
c1="E32"
lat=dted_ops.GeoCoord(c0)
lon=dted_ops.GeoCoord(c1)
coords =(lat,lon)

print(f"dted_reader height: {dted_reader.get_height(coords,1,dted_ops.HeightQuery.INTERPOLATE)}     {custom_reader_data[1200][0]}")



c0="N39.99958368026644"
c1="E32.99958368026644"
lat=dted_ops.GeoCoord(c0)
lon=dted_ops.GeoCoord(c1)
coords =(lat,lon)

print(f"dted_reader height: {dted_reader.get_height(coords,1,dted_ops.HeightQuery.INTERPOLATE)}     {custom_reader_data[1200][1200]}")






gdal_data=gdal.Open(DTED_FILE_PATH).ReadAsArray()







#for i in range(1201):
#    for j in range(1201):
#        print(f"{i}-{j}:   custom_reader_data: {gdal_data[i][j]}  ")
#        print(f"{i+j}:   custom_reader_data: {custom_reader_data[i][j]}         gdal_data: {gdal_data[i][j]}")














#for visualization
#import bmesh
#from mathutils import Vector
#density=20
#collection = bpy.data.collections["Collection"]

##_____________________________________________________________________________________________________________________
#mesh = bpy.data.meshes.new("custom_reader_mesh")  # add a new mesh
#custom_reader_dted_obj = bpy.data.objects.new("custom_reader_dted_obj", mesh)  # add a new object using the mesh
#collection.objects.link(custom_reader_dted_obj)  # put the object into the scene (link)
#mesh = custom_reader_dted_obj.data
#bm = bmesh.new()

#for i in range(-600,601):
#    for j in range(-600,601):
#        v=Vector((i*density,j*density,custom_reader_data[i+600][j+600]))
#        bm.verts.new(v)

## make the bmesh the object's mesh
#bm.to_mesh(mesh)  
#bm.free()  # always do this when finished

##_____________________________________________________________________________________________________________________
#mesh = bpy.data.meshes.new("gdal_mesh")  # add a new mesh
#gdal_dted_obj = bpy.data.objects.new("gdal_dted_obj", mesh)  # add a new object using the mesh
#collection.objects.link(gdal_dted_obj)  # put the object into the scene (link)
#mesh = gdal_dted_obj.data
#bm = bmesh.new()

#for i in range(-600,601):
#    for j in range(-600,601):
#        v=Vector((i*density,j*density,gdal_data[i+600][j+600]))
#        bm.verts.new(v)

## make the bmesh the object's mesh
#bm.to_mesh(mesh)  
#bm.free()  # always do this when finished
##_____________________________________________________________________________________________________________________


##for i in range(0,100):
##    for j in range(0,100):
##        print(f"[{i}][{j}]   custom_reader_data: {custom_reader_data.data[i][j]}   gdal_data: {gdal_data[j][i]}")