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

import re
import glob, os
from mathutils import Vector
from time import time

from queue import PriorityQueue
from dataclasses import dataclass, field
from typing import Any
import numpy as np

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

PARTITION_DEVIDER = 6

# -----------------------------------------------------------------------------
# Class Definitions

class Vert():

    def __init__(self, vertex):
        
        self.vert_x = vertex[0]
        self.vert_y = vertex[1]
        self.vert_z = vertex[2]

    def write_binary(self, file_handle):

        file_handle.write(struct.pack('f', self.vert_x))
        file_handle.write(struct.pack('f', self.vert_y))
        file_handle.write(struct.pack('f', self.vert_z))


def get_lan_lon_from_foldername(folder_name):
    # Folder are in format N40E032. Extract +39 and +32 as lat-lon
    if len(folder_name) != 7:
        print(f"DTED file name is not correct {folder_name}")
        sys.exit(-1)
    else:
        lat = int(folder_name[1:3])
        lon = int(folder_name[4:7])
        if folder_name[0] == 'S':
            lat = -1 * lat
        if folder_name[3] == 'W':
            lon = -1 * lon

        return lat, lon


def download_osm_files(lat,lon,dist):
    bpy.context.scene.blosm.maxLat = lat+dist
    bpy.context.scene.blosm.minLat = lat-dist
    bpy.context.scene.blosm.maxLon = lon+dist
    bpy.context.scene.blosm.minLon = lon-dist    
    

    ##Esenboga ex.
    #bpy.context.scene.blosm.maxLat = 40.1500
    #bpy.context.scene.blosm.minLat = 40.1000
    #bpy.context.scene.blosm.maxLon = 33.0150
    #bpy.context.scene.blosm.minLon = 32.9700

    ##Esenboga ex.
    #bpy.context.scene.blosm.maxLat = 40.1450
    #bpy.context.scene.blosm.minLat = 40.1350
    #bpy.context.scene.blosm.maxLon = 33
    #bpy.context.scene.blosm.minLon = 32.9850



    #Select only forests
    bpy.context.scene.blosm.buildings = False
    bpy.context.scene.blosm.water = False
    bpy.context.scene.blosm.vegetation = False
    bpy.context.scene.blosm.highways = False
    bpy.context.scene.blosm.railways = False


    bpy.context.scene.blosm.forests = True
    bpy.context.scene.blosm.ignoreGeoreferencing = True


    bpy.ops.blosm.import_data()



def line_intersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        return False,0,0
       #raise Exception('lines do not intersect')

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return True,x, y


@dataclass(order=True)
class PrioritizedEdgeItem:
    priority: int
    item: Any=field(compare=False)


def get_tee_points(mesh,bbox,tree_resolution):

    def get_vector_by_index(v_index):
        return mesh.vertices[v_index]

    def get_vectors_from_edge(edge):
        return get_vector_by_index(edge.vertices[0]),get_vector_by_index(edge.vertices[1])

    def get_max_y_vector_from_edge(edge):
        return max(get_vector_by_index(edge.vertices[0]).co.y,get_vector_by_index(edge.vertices[1]).co.y)
    def get_min_y_vector_from_edge(edge):
        return min(get_vector_by_index(edge.vertices[0]).co.y,get_vector_by_index(edge.vertices[1]).co.y)
    def get_max_x_vector_from_edge(edge):
        return max(get_vector_by_index(edge.vertices[0]).co.x,get_vector_by_index(edge.vertices[1]).co.x)
    def get_min_x_vector_from_edge(edge):
        return min(get_vector_by_index(edge.vertices[0]).co.x,get_vector_by_index(edge.vertices[1]).co.x)

    planted_trees =0
    placed_trees = []

    edge_queue = PriorityQueue()
    min_vector=Vector((0,0))

    for edge in mesh.edges:
        min_y_val =get_min_y_vector_from_edge(edge)
        min_x_val =get_min_x_vector_from_edge(edge)

        if(min_vector.x>min_x_val):
            min_vector.x=min_x_val
        if(min_vector.y>min_y_val):
            min_vector.y=min_y_val

        edge_queue.put(PrioritizedEdgeItem(min_y_val,edge))
        
    max_vector=Vector((bbox[0]+min_vector.x,bbox[1]+min_vector.y))

    intersection_check_list=[]
    intersections=PriorityQueue()

    rayDir = Vector((min_vector.x,max_vector.x))
    
    for rayHeight in np.arange(min_vector.y, max_vector.y, tree_resolution):

        #empty intersections
        while ((not intersections.empty())):
            intersections.get()
            
        while ((not edge_queue.empty()) and (edge_queue.queue[0].priority<= rayHeight)):			
            intersection_check_list.append(edge_queue.get())
		
        #fliter out passed edges
        #intersection_check_list=[candidate_edge for candidate_edge in intersection_check_list if max(mesh.vertices[candidate_edge.item.vertices[0]].co.y,mesh.vertices[candidate_edge.item.vertices[1]].co.y)>=rayHeight]
        intersection_check_list=[candidate_edge for candidate_edge in intersection_check_list if get_max_y_vector_from_edge(candidate_edge.item)>=rayHeight]

        for candidate_edge in intersection_check_list:
            v1,v2=get_vectors_from_edge(candidate_edge.item)
            intersection = line_intersection((v1.co,v2.co),((rayDir[0],rayHeight),(rayDir[1],rayHeight)))
            if(intersection[0]):
                intersections.put(intersection[1],Vector( (intersection[1],intersection[2],0) ))
                

        placed_treesRow = []


        if(len(intersections.queue)%2==1):
            raise Exception('Need 2 points')

        if(len(intersections.queue)==0):
            continue

        while ((not intersections.empty())):
            x1=intersections.get()
            x2=intersections.get()

            for tree_point_x in np.arange(x1,x2, tree_resolution):
                placed_treesRow.append(Vector((tree_point_x,rayHeight,0)))
                planted_trees+=1                
                
        placed_trees.append(placed_treesRow)


    print(f"***** Finished    |   {planted_trees} trees are planted :)       **********")
    return placed_trees


def print_seperator():
    print('#### ---- #### ---- #### ---- ####')


# -----------------------------------------------------------------------------
# Script starts here

def main(argv):

    # Get arguments from argv
    OSM_DIR = argv[5]
    OUT_TYPE = f'.{argv[6]}'
    global OUTPUT_BINARY
    # Set correct algorithm for calculating positions
    if OUT_TYPE == '.bin':
        OUTPUT_BINARY = True
    elif OUT_TYPE == '.fbx':
        OUTPUT_BINARY = False
        
    #get lan lon from folder name
    lat,lon = get_lan_lon_from_foldername(os.path.basename(OSM_DIR))
    print(f"lat: {lat} lon:{lon}")

    lat=40.14
    lon=32.9925

    #obj_ops.clear_all_except_collection("Collection")
    #download_osm_files(lat,lon,0.01)
    
    obj = obj_ops.get_obj_endswith(".osm_forest")
    obj_mesh=obj.data
    bbox = obj.dimensions
    tree_resolution =10
    tree_points = get_tee_points(obj_mesh,bbox,tree_resolution)


    #old_translate_pivot = obj_ops.get_obj_include('TranslateObj')
    #if(old_translate_pivot):
    #    bpy.ops.object.select_all(action='DESELECT')
    #    old_translate_pivot.select_set(True)
    #    bpy.data.objects.remove(old_translate_pivot, do_unlink=True)

    #translate_pivot = bpy.data.objects.new( 'TranslateObj', None )    
    #bpy.context.scene.collection.objects.link(translate_pivot)
    #translate_pivot.rotation_euler = (0,0,0)


    #translate_pivot.matrix_world.translation+= Vector((0,180,0))

    #obj_ops.correct_transform(translate_pivot,(0,0,0),(0,0,0))
    

    export_data=[]
    for tree_row in tree_points:
        for tree_point in tree_row:
            #tree_point = obj_ops.translate_point_by_obj(tree_point,(0,0,0),(0,90,0))
            #tree_point=obj_ops.translate_point_by_obj(tree_point,(0,0,0),(0,0,90))
            export_data.append(Vert(tree_point))


    #old_translate_pivot = obj_ops.get_obj_include('TranslateObj')
    #if(old_translate_pivot):
    #    bpy.ops.object.select_all(action='DESELECT')
    #    old_translate_pivot.select_set(True)
    #    bpy.data.objects.remove(old_translate_pivot, do_unlink=True)

    obj_ops.clear_transform_obj()
    


    io_ops.export_bin_file(export_data,OSM_DIR,"tree",".treedata")


    #for tree_row in tree_points:
    #    for tree_point in tree_row:
    #        bpy.ops.mesh.primitive_cube_add(location=tree_point)


    # # Export results
    # export_results(OUTPUT_DIR, dted_file, OUT_TYPE)
        

    # print(f'Script is now complete. Please see {OUTPUT_DIR} directory for results')


if __name__ == '__main__':
    arguments = []
    arguments.append('_') # argv[0], Blender exe path
    arguments.append('_') # argv[1], .blend file path
    arguments.append('_') # argv[2], '--background', run script w/o Blender UI
    arguments.append('_') # argv[3], '--python'
    arguments.append('_') # argv[4], python script path
    arguments.append('D:\\Assets\\OsmData\\N40E032') # argv[5], Osm file directory
    arguments.append('bin') # argv[6], output file extension ('bin' or 'fbx')
    main(arguments)
    # main(sys.argv)
