import os
import sys
import time
import imp
import bmesh
import numpy as np;
import bpy

#DTED_FILE_PATH = os.path.join(BLENDER_DIR,SCRIPTS_PATH,"resources","DTED","N39E032.dt1")
#DTED_FOLDER_PATH = os.path.join(BLENDER_DIR,SCRIPTS_PATH,"resources","DTED")


##def read_dted_using_gdal(file_path):    

##    # Read file with GDAL
##    src_ds = gdal.Open(file_path)
##    # Get height map
##    height_map = src_ds.ReadAsArray()

##    #print(height_map)
##    return height_map


##def read_dted_using_custom_reader(file_path):
##    file_name,file_extension,coords = dted_ops.resolve_dted_file(file_path)    
##    dted= dted_ops.DTED(file_path)
##    return np.array(dted.data)



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


def create_mesh(verts):
    mesh = bpy.data.meshes.new("mesh")  # add a new mesh
    obj = bpy.data.objects.new("MyObject", mesh)  # add a new object using the mesh

    scene = bpy.context.scene
    scene.objects.link(obj)  # put the object into the scene (link)
    scene.objects.active = obj  # set as the active object in the scene
    obj.select = True  # select object

    mesh = bpy.context.object.data
    bm = bmesh.new()

    for v in verts:
        bm.verts.new(v)  # add a new vert

    # make the bmesh the object's mesh
    bm.to_mesh(mesh)  
    bm.free()  # always do this when finished



def import_script(script_path):
    return imp.load_source(os.path.basename(script_path), script_path)

def get_executable_script(script_path):
    return compile(open(script_path).read(), script_path, 'exec')

def main(argv):
    # Get arguments from argv
    DTED_OPS_DIR = argv[6]
    DTED_DIR = argv[7]
    OUTPUT_DIR = argv[8]
    LAT_MIN = argv[9]
    LON_MIN = argv[10]
    LAT_MAX = argv[11]
    LON_MAX = argv[12]
    RESOLUTION = float(argv[13])

    dted_ops=import_script(DTED_OPS_DIR)

    if os.path.exists(DTED_DIR):

        dted_reader=dted_ops.DTED(DTED_DIR)        
        if(OUTPUT_DIR =="" ):
            OUTPUT_DIR = os.path.join(DTED_DIR, '_Results')        
        print(f'OUTPUT_DIR is  {OUTPUT_DIR}')
        

        coords_min =(dted_ops.GeoCoord(LAT_MIN),dted_ops.GeoCoord(LON_MIN))
        coords_max =(dted_ops.GeoCoord(LAT_MAX),dted_ops.GeoCoord(LON_MAX))

        
        coords_min_desired_height_interpolated = dted_reader.get_dted_height_interpolated(coords_min)
        print(f"interpolated height at coords_min coords {str(coords_min[0])},{str(coords_min[1])}:  {coords_min_desired_height_interpolated}")

        coords_max_desired_height_interpolated = dted_reader.get_dted_height_interpolated(coords_max)
        print(f"interpolated height at coords_max coords {str(coords_max[0])},{str(coords_max[1])}:  {coords_max_desired_height_interpolated}")
        

        height_map=dted_reader.get_height_map((coords_min,coords_max),RESOLUTION)

        create_mesh([(np.where(height_map==height),height) for height in height_map])
        #create_mesh([vert for vert in (np.where(height_map==height),height) for height in height_map])

        ##Example
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




    else:
        print(f'ERROR:    DTED directory {DTED_DIR} cannot be found. Please try again.')



if __name__ == '__main__':
    # For running the script inside Blender, see outside usage from 'GenerateTurkey.bat'
    # arguments = []
    # arguments.append('_') # argv[0], Blender exe path
    # arguments.append('_') # argv[1], .blend file path
    # arguments.append('_') # argv[2], '--background', run script w/o Blender UI
    # arguments.append('_') # argv[3], '--python'
    # arguments.append('_') # argv[4], python script path
    # arguments.append('_') # argv[5], '--python'
    # arguments.append('_') # argv[6], DTED OPS py file
    # arguments.append('_') # argv[7], DTED file directory
    # arguments.append('_') # argv[8], Output file directory
    
    # arguments.append('_') # argv[9], lat/lon min
    # arguments.append('_') # argv[10], lat/lon max

    # arguments.append('_') # argv[11], lat/lon min
    # arguments.append('_') # argv[12], lat/lon max
    # arguments.append('_') # argv[13], map resolution
    main(sys.argv)

