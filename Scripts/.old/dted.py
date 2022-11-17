import os
import sys
import re
import bpy
import bmesh
import math
import struct
import numpy as np
import time
from osgeo import gdal

# -----------------------------------------------------------------------------
# Settings

DEG_2_RAD = (math.pi / 180)
# DTED files represent elevation data with 1201 * 1201 entries
DTED_LEN = 1201
ZERO = 0
DEGREE_INCREMENT = 1 / 1200
# We will divide 1 DTED file into 36 with 201 * 201 entries
LIL_DTED_LEN = 201 # Note: There is overlapping
EARTH_RADIUS = 6378137  # in meters
FLATTENING = 0.0033528106647474805 # 1/298.257223563
E2 = 0.0066943799901413165 # FLATTENING * (2-FLATTENING)
INVALID_DTED = -32767
OUTPUT_BINARY = False

# -----------------------------------------------------------------------------
# Class Definitions

class Vert():

    def __init__(self, vertex):

        self.index = vertex.index
        self.vert_x = vertex.co[0]
        self.vert_y = vertex.co[1]
        self.vert_z = vertex.co[2]
        self.norm_x = vertex.normal[0]
        self.norm_y = vertex.normal[1]
        self.norm_z = vertex.normal[2]
        # uv's to be filled later
        self.u = -1
        self.v = -1

    def set_uv(self, uv_data):

        if self.u == -1:
            self.u = uv_data[0]
        elif self.u != uv_data[0]:
            print(f'Mismatch between two u s {self.u} not eq {uv_data[0]}')
        if self.v == -1:
            self.v = uv_data[1]
        elif self.v != uv_data[1]:
            print(f'Mismatch between two v s {self.v} not eq {uv_data[1]}')

    def write_binary(self, file_handle):

        file_handle.write(struct.pack('f', self.vert_x))
        file_handle.write(struct.pack('f', self.vert_y))
        file_handle.write(struct.pack('f', self.vert_z))
        file_handle.write(struct.pack('f', self.norm_x))
        file_handle.write(struct.pack('f', self.norm_y))
        file_handle.write(struct.pack('f', self.norm_z))
        file_handle.write(struct.pack('f', self.u))
        file_handle.write(struct.pack('f', self.v))

# -----------------------------------------------------------------------------
# Utility Functions

def lla2ecef_blender(lat, lon, altitude):

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

def lla2ecef_unity(lat, lon, altitude):

    lat_rad = lat * DEG_2_RAD
    lon_rad = lon * DEG_2_RAD

    sinphi = math.sin(lat_rad)
    cosphi = math.cos(lat_rad)

    N = EARTH_RADIUS / (1 - E2 * sinphi ** 2) ** 0.5
    rho = (N + altitude) * cosphi

    y = (N * (1 - E2) + altitude) * sinphi
    x = rho * math.cos(lon_rad)
    z = rho * math.sin(lon_rad)

    on_earth_pos = np.array([x, y, z])

    return on_earth_pos

def lla2ecef(lat, lon, altitude):
    
    if OUTPUT_BINARY:
        return lla2ecef_unity(lat, lon, altitude)
    else:
        return lla2ecef_blender(lat, lon, altitude)

def calculate_faces_uvs(dted_len):

    faces = []
    uvs = []
    mult_fact = 1 / (dted_len - 1)

    for i in range(dted_len * (dted_len - 1)):
        # End of row, need to start the next row
        if i % dted_len == dted_len - 1:
            continue
        else:
            if OUTPUT_BINARY:
                faces.append((i, i + 1, i + dted_len))
                uvs.append(((i // dted_len) * mult_fact, 1 - (i % dted_len) * mult_fact))
                uvs.append((((i + 1) // dted_len) * mult_fact, 1 - ((i + 1) % dted_len) * mult_fact))
                uvs.append((((i + dted_len) // dted_len) * mult_fact, 1 - ((i + dted_len) % dted_len) * mult_fact))

                faces.append((i + dted_len, i + 1, i + dted_len + 1))
                uvs.append((((i + dted_len) // dted_len) * mult_fact, 1 - ((i + dted_len) % dted_len) * mult_fact))
                uvs.append((((i + 1) // dted_len) * mult_fact, 1 - ((i + 1) % dted_len) * mult_fact))
                uvs.append((((i + dted_len) // dted_len) * mult_fact, 1 - ((i + 1) % dted_len) * mult_fact))
            else:
                faces.append((i, i + dted_len, i + 1))
                uvs.append(((i // dted_len) * mult_fact, (i % dted_len) * mult_fact))
                uvs.append((((i + dted_len) // dted_len) * mult_fact, ((i + dted_len) % dted_len) * mult_fact))
                uvs.append((((i + 1) // dted_len) * mult_fact, ((i + 1) % dted_len) * mult_fact))

                faces.append((i + dted_len, i + dted_len + 1, i + 1))
                uvs.append((((i + dted_len) // dted_len) * mult_fact, ((i + dted_len) % dted_len) * mult_fact))
                uvs.append((((i + dted_len) // dted_len) * mult_fact, ((i + 1) % dted_len) * mult_fact))
                uvs.append((((i + 1) // dted_len) * mult_fact, ((i + 1) % dted_len) * mult_fact))

    return faces, uvs

def export_results(output_dir, file_name, file_extension):

    # Only .fbx and .bin are accepted as file_extension
    if file_extension == '.fbx' or file_extension == '.bin':
        # Get rid of the '.dt1' extension from file name
        file_name = file_name[:-4]
        dir_name = file_name[:7]

        if not os.path.exists(os.path.join(output_dir, dir_name, file_extension[1:])):
            os.makedirs(os.path.join(output_dir, dir_name, file_extension[1:]))

        for obj in bpy.data.objects:
            # Need to select one object for export
            bpy.ops.object.select_all(action = 'DESELECT')
            obj.select_set(True)

            # Creates the path for the exported fbx.
            obj_name = generate_export_name(obj)

            # Export
            if file_extension == '.fbx':
                obj_path = os.path.join(output_dir, dir_name, file_extension[1:], obj_name + file_extension)
                bpy.ops.export_scene.fbx(filepath = obj_path, use_selection = True, axis_forward = '-Z', axis_up = 'Y')
            elif file_extension == '.bin':
                export_as_bin(obj, obj_name, output_dir, dir_name)
    else:
        print(f'Results cannot be exported in {file_extension} format, you must use .fbx or .bin')

    # Unselect the last object
    bpy.ops.object.select_all(action='DESELECT')

def export_as_bin(obj, obj_name, output_dir, dir_name):
    
    vertices = []
    indices = []
    for vert in obj.data.vertices:
        vertices.append(Vert(vert))
    for poly in obj.data.polygons:
        for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
            vertices[obj.data.loops[loop_index].vertex_index].set_uv(obj.data.uv_layers[0].data[loop_index].uv)
            indices.append(obj.data.loops[loop_index].vertex_index)

    vert_path = os.path.join(output_dir, dir_name, 'bin', obj_name + '.vert')
    with open(vert_path, 'wb') as vf:
        for vertex in vertices:
            vertex.write_binary(vf)

    idx_path = os.path.join(output_dir, dir_name, 'bin', obj_name + '.ind')
    with open(idx_path, 'wb') as idf:
        for index in indices:
            idf.write(struct.pack('H', index))

def generate_export_name(obj):
    
    # Name the objects such that they are the same as the images.
    name_lst = []
    if '.' in obj.name:
        obj_index = int(obj.name[8:-4])
    else: # type is object
        obj_index = int(obj.name[8:])
    obj_lat_idx = obj_index % 6
    obj_lon_idx = obj_index // 6
    obj_lat_idx = str(obj_lat_idx + 1) # they start from 1 instead of 0
    obj_lon_idx = str(obj_lon_idx + 1)
    name_lst.append(obj.name[1:3])
    name_lst.append(obj_lat_idx)
    name_lst.append(str(int(obj.name[4:7])))
    name_lst.append(obj_lon_idx)

    return "_".join(name_lst)


def read_dted_data(dted_dir, dted_file):

    # Read file with GDAL
    src_ds = gdal.Open(os.path.join(dted_dir, dted_file))
    print("opened")
    print(src_ds)
    # Get height map
    height_map = src_ds.ReadAsArray()
    # Replace invalid DTED values
    height_map = get_rid_of_invalid_dted(height_map)
    # height_map = get_rid_of_invalid_dted(height_map)
    # Get lat, lon for calculating base points coordinates
    lat, lon = get_lat_lon_from_filename(dted_file)
    # Calculate base XYZ position for sea level
    base_pos = lla2ecef(lat, lon, ZERO)

    return height_map, base_pos

def get_rid_of_invalid_dted(height_map):
    
    # Find invalid values in height_map
    height_map = np.ma.masked_array(height_map, height_map == INVALID_DTED)
    before_count = np.ma.count_masked(height_map) # For debugging
    # Replace invalid values with close neighbors
    for shift in (-1,1):
        for axis in (1,0):        
            height_map_shifted = np.roll(height_map, shift=shift, axis=axis)
            idx = ~height_map_shifted.mask * height_map.mask
            height_map[idx] = height_map_shifted[idx]
    # Sometimes, even after running the code above doesn't fix the problem.
    # In that case, recursive calls may be necessary
    height_map = np.ma.masked_array(height_map, height_map == INVALID_DTED)
    if np.ma.count_masked(height_map) > 0:
        height_map = get_rid_of_invalid_dted(height_map)
    after_count = np.ma.count_masked(height_map) # For debugging
    print(f'{before_count - after_count} invalid DTED values are interpolated')

    return height_map

def get_lat_lon_from_filename(file_name):

    # DTED files are in format N39E032.dt1. Extract +39 and +32 as lat-lon
    if len(file_name) != 11:
        print(f"DTED file name is not correct {file_name}")
        sys.exit(-1)
    else:
        lat = int(file_name[1:3])
        lon = int(file_name[4:7])
        if file_name[0] == 'S':
            lat = -1 * lat
        if file_name[3] == 'W':
            lon = -1 * lon

        return lat, lon

def delete_prev_objs():

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def calculate_positions(lat, lon, height_map, base_pos):
    
    positions = np.empty((DTED_LEN, DTED_LEN, 3))
    for i in range(DTED_LEN):
        for j in range(DTED_LEN):
            #positions[i, j] = xyz_pos(lat + DEGREE_INCREMENT * j, lon + DEGREE_INCREMENT * i, height_map[1200 - j, i]) - base_pos
            positions[i, j] = lla2ecef(lat + DEGREE_INCREMENT * j, lon + DEGREE_INCREMENT * i, height_map[1200 - j, i]) - base_pos

    return positions

def calculate_verts_faces_uvs(positions):

    verts = []
    uvs = []
    # Flatten the positions for calculating indices
    pos_flat = np.reshape(positions, (DTED_LEN * DTED_LEN, 3))

    # Loop like this because we need to divide 1 big DTED data into 36
    for i in range(6):
        for j in range(6):
            temp = []
            for k in range(LIL_DTED_LEN):
                for m in range(LIL_DTED_LEN):
                    idx = ((k + (LIL_DTED_LEN - 1) * i) * DTED_LEN) + m + ((LIL_DTED_LEN - 1) * j)
                    temp.append((pos_flat[idx][0], pos_flat[idx][1], pos_flat[idx][2]))
            verts.append(temp)

    faces, uvs = calculate_faces_uvs(LIL_DTED_LEN)

    return verts, faces, uvs

def generate_mesh_objects_with_uvs(verts, faces, dted_file, uvs):

    dted_name = dted_file[:-4]

    for i in range(36):
        mesh_name = f"{dted_name}_{i}"
        mesh = bpy.data.meshes.new(mesh_name)
        mesh.from_pydata(verts[i], [], faces)

        obj = bpy.data.objects.new(mesh_name, mesh)
        # Rotate 180 degrees in Z to solve the orientation problem in Unity
        #obj.rotation_euler = (0, 0, math.radians(-180))
        
        # Move the object under Collection
              
            
        try:
            collection = bpy.data.collections["Collection"]
        except:                
            collection = bpy.data.collections.new("Collection")
            bpy.context.scene.collection.children.link(collection)

        collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj

        me = obj.data
        #if bpy.ops.context.active_object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(me)

        uv_layer = bm.loops.layers.uv.verify()

        # adjust uv coordinates
        idx = 0
        for face in bm.faces:
            for loop in face.loops:
                loop_uv = loop[uv_layer]
                # use xy position of the vertex as a uv coordinate
                loop_uv.uv = uvs[idx]
                # print(f"loop uv line {loop.vert.co.xy}")
                idx += 1

    rename_number_correction()
    
    # Set object mode to Object mode - default
    bpy.ops.object.mode_set()

def rename_number_correction():
    for ob in bpy.data.objects:
        oname = ob.name
        matnum = re.search("\d\d\d$", oname)
        if matnum:
            ob.name = (ob.name.rstrip(ob.name[-4:]))

def smoothen_meshes():
    
    bpy.ops.object.mode_set()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.shade_smooth()

def reduce_size():
    # Need to decimate all objects
    for obj in bpy.data.objects:
        bpy.ops.object.select_all(action = 'DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        bpy.ops.object.modifier_add(type='DECIMATE')
        bpy.context.object.modifiers["Decimate"].ratio = 0.3
        bpy.ops.object.modifier_apply(modifier="Decimate")

        bpy.ops.object.modifier_add(type='WEIGHTED_NORMAL')
        bpy.context.object.modifiers["WeightedNormal"].weight = 30
        bpy.ops.object.modifier_apply(modifier="WeightedNormal")

        # This is replacing the 'smothen_meshes' method
        #obj.data.use_auto_smooth = True

def print_seperator():
    print('#### ---- #### ---- #### ---- ####')


# -----------------------------------------------------------------------------
# Script starts here

def main(argv):

    # Get arguments from argv
    DTED_DIR = argv[5]
    OUT_TYPE = f'.{argv[6]}'
    global OUTPUT_BINARY
    # Set correct algorithm for calculating positions
    if OUT_TYPE == '.bin':
        OUTPUT_BINARY = True
    elif OUT_TYPE == '.fbx':
        OUTPUT_BINARY = False

    # Determine which files need to be processed
    dted_files = []
    if os.path.exists(DTED_DIR):
        print(f'Started parsing elevation data under {DTED_DIR} directory')
        dted_files = os.listdir(DTED_DIR)
        dted_files = [dted_file for dted_file in dted_files if dted_file.endswith('.dt1')]
        OUTPUT_DIR = os.path.join(DTED_DIR, '_Results')
    else:
        print(f'DTED directory {DTED_DIR} cannot be found. Please try again.')
        time.sleep(10)
        sys.exit(-1)

    # Handle previous results if necessary

    print(f'OUTPUT_DIR is set to {OUTPUT_DIR}')
    print_seperator() # For pretty console output

    # Model every dted file in dted directory
    for dted_file in dted_files:

        # Delete previous objects
        delete_prev_objs()

        # Get lat, lon from file name
        lat, lon = get_lat_lon_from_filename(dted_file)

        # Calculate height map and base_pos
        height_map, base_pos = read_dted_data(DTED_DIR, dted_file)

        # Calculate positions
        positions = calculate_positions(lat, lon, height_map, base_pos)

        # Calculate verts, faces and UVs
        verts, faces, uvs = calculate_verts_faces_uvs(positions)

        # Generate mesh objects with UVs
        generate_mesh_objects_with_uvs(verts, faces, dted_file, uvs)

        # Reduce size using decimate and weighted normals
        # reduce_size()

        # Use interpolated vertex normals for smooth shading
        smoothen_meshes()
        # use_auto_smooth is used instead in reduce_size() method

        # Export results
        export_results(OUTPUT_DIR, dted_file, OUT_TYPE)
        
        print(f'Generated 3d models of {dted_file}')
        print_seperator() # For pretty console output

    print(f'Script is now complete. Please see {OUTPUT_DIR} directory for results')


if __name__ == '__main__':
    # For running the script inside Blender, see outside usage from 'GenerateTurkey.bat'
    arguments = []
    arguments.append('_') # argv[0], Blender exe path
    arguments.append('_') # argv[1], .blend file path
    arguments.append('_') # argv[2], '--background', run script w/o Blender UI
    arguments.append('_') # argv[3], '--python'
    arguments.append('_') # argv[4], python script path
    arguments.append('D:\\Assets\\DtedData\\N40_E32') # argv[5], DTED file directory
    arguments.append('bin') # argv[6], output file extension ('bin' or 'fbx')
    main(arguments)
    # main(sys.argv)
