import os
import sys
import time
import imp
import bmesh
import numpy as np;
import bpy

#DTED_FILE_PATH = os.path.join(PROJECT_DIR,"Resources","DTED","N39E032.dt1")
DTED_FOLDER_PATH = os.path.join(PROJECT_DIR,"Resources","DTED")
DTED_FOLDER_OUTPUT_PATH = os.path.join(PROJECT_DIR,"Resources","TerrainModels")

def create_mesh(verts):

    mesh = bpy.data.meshes.new("Dted Mesh")
    dted_terrain = bpy.data.objects.new( 'Dted Terrain', mesh )
    bpy.context.scene.collection.objects.link(dted_terrain)
    bm = bmesh.new()

    #row, col = height_map.shape
    #for x in range(0,row):
    #    for y in range(0,col):
    #        bm.verts.new((row,col,height_map[row][col]))

    for v in verts:
        #print(v)
        bm.verts.new(v)  # add a new vert

    # make the bmesh the object's mesh
    bm.to_mesh(mesh)
    bm.free()  # always do this when finished



def create_dted_mesh(LAT_MIN,LON_MIN,LAT_MAX,LON_MAX,RESOLUTION,SCALE_FACTOR):

        coords_min =(dted_ops.GeoCoord(LAT_MIN),dted_ops.GeoCoord(LON_MIN))
        coords_max =(dted_ops.GeoCoord(LAT_MAX),dted_ops.GeoCoord(LON_MAX))


        #coords_min_desired_height_interpolated = dted_reader.get_dted_height_interpolated(coords_min)
        #print(f"interpolated height at coords_min coords {str(coords_min[0])},{str(coords_min[1])}:  {coords_min_desired_height_interpolated}")

        #coords_max_desired_height_interpolated = dted_reader.get_dted_height_interpolated(coords_max)
        #print(f"interpolated height at coords_max coords {str(coords_max[0])},{str(coords_max[1])}:  {coords_max_desired_height_interpolated}")


        #height_map=dted_reader.get_height_map((coords_min,coords_max),RESOLUTION,SCALE_FACTOR,dted_ops.HeightQuery.INTERPOLATE)
        height_map=dted_reader.get_height_map((coords_min,coords_max),RESOLUTION,SCALE_FACTOR,dted_ops.HeightQuery.NEAREST)

        create_mesh(height_map)


if os.path.exists(DTED_FOLDER_PATH):

    dted_reader=dted_ops.DTED(DTED_FOLDER_PATH)
    if(DTED_FOLDER_OUTPUT_PATH =="" ):
        OUTPUT_DIR = os.path.join(DTED_FOLDER_PATH, '_Results')
        print(f'OUTPUT_DIR is  {DTED_FOLDER_OUTPUT_PATH}')
    else:
        print(f'ERROR:    DTED directory {DTED_FOLDER_PATH} cannot be found. Please try again.')



#create_dted_mesh("N39.856", "E32.925", "N40.152", "E33.228", 1,20)
#create_dted_mesh("N38.986", "E31.987", "N41.023", "E34.015", 1,20)

#ESB
#c1=dted_ops.GeoCoord("N40.128101")
#c2=dted_ops.GeoCoord("E32.995098")


c1=dted_ops.GeoCoord("N40.078899")
c2=dted_ops.GeoCoord("E32.565601")
coords=(c1,c2)

print(dted_reader.get_height( coords,1,dted_ops.HeightQuery.NEAREST))
