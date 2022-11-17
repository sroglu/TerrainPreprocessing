import bpy
import bmesh
import re
import os
import math
import numpy as np


def get_obj_include(obj_name):
    for ob in bpy.data.objects:
        matnum = re.search(".*"+obj_name+".*", ob.name)
        if matnum:
            return ob
        
def get_obj_startswith(obj_name):
    for ob in bpy.data.objects:
        matnum = re.search(obj_name+".*", ob.name)
        if matnum:            
            return ob
        
def get_obj_endswith(obj_name):
    for ob in bpy.data.objects:
        matnum = re.search(".*"+obj_name, ob.name)
        if matnum:
            return ob

def default_export(export_name):
    blend_export_file_path =  os.path.join(PROJECT_DIR,"Exports")
    if not os.path.exists(blend_export_file_path):
    	os.makedirs(blend_export_file_path)

    target_file = os.path.join(blend_export_file_path, export_name)
    bpy.ops.export_scene.fbx(filepath=target_file,use_space_transform=False, bake_space_transform=False)
        
def correct_transform(obj,position,rotation):
    obj.select_set(True)
    obj.parent = None
    obj.rotation_mode = 'XYZ'
    
    x=rotation[0]
    y=rotation[1]
    z=rotation[2]    
    
    old_obj=get_obj_startswith("Pivot")
    if(old_obj):
        bpy.ops.object.select_all(action='DESELECT')
        old_obj.select_set(True)
        bpy.data.objects.remove(old_obj, do_unlink=True)        

    pivot_vertex = bpy.data.objects.new( 'Pivot', None )
    bpy.context.scene.collection.objects.link(pivot_vertex)
    pivot_vertex.rotation_euler = (0,0,0)

    old_pxy=get_obj_include("PivotXY")
    if (old_pxy):
        bpy.ops.object.select_all(action='DESELECT')
        old_pxy.select_set(True)
        bpy.data.objects.remove(old_pxy, do_unlink=True)

    pivot_vertex_xy = bpy.data.objects.new( 'PivotXY', None )
    bpy.context.scene.collection.objects.link(pivot_vertex_xy)
    pivot_vertex_xy.parent = pivot_vertex
    pivot_vertex_xy.rotation_euler = (0,0,0)

    old_pz=get_obj_include("PivotZ")
    if (old_pz):
        bpy.ops.object.select_all(action='DESELECT')
        old_pz.select_set(True)
        bpy.data.objects.remove(old_pz, do_unlink=True)

    pivot_vertex_z = bpy.data.objects.new( 'PivotZ', None )
    bpy.context.scene.collection.objects.link(pivot_vertex_z)
    pivot_vertex_z.parent = pivot_vertex_xy
    pivot_vertex_z.rotation_euler = (0,0,0)
        
    obj.parent = pivot_vertex_z    
    #pivot_vertex.rotation_euler = (0,math.pi/2,math.pi/2)
    pivot_vertex.rotation_euler = (0,0,0)
    pivot_vertex_xy.rotation_euler = (math.radians(x), math.radians(-y), 0)
    pivot_vertex_z.rotation_euler = (0, 0, math.radians(-z))
    #obj.rotation_euler=(0,0,0)
    obj.rotation_euler = (0,-math.pi/2,0)
    obj.location=(0,0,0)
    
    #pivot_vertex.scale =(1,1,1)
    #pivot_vertex_xy.scale =(1,1,1)
    #pivot_vertex_z.scale =(1,1,1)
    #obj.scale =(1,1,1)    
    
    pivot_vertex.location =(0,0,0)
    pivot_vertex_xy.location =(0,0,0)
    pivot_vertex_z.location =(0,0,0)
    obj.location =(0,0,0)    
    
    
    pivot_vertex.location=(-position[0],position[1],position[2])
    
    return pivot_vertex

def clear_transform_obj():
    old_obj=get_obj_startswith("Pivot")
    if(old_obj):
        old_obj.select_set(True)
        bpy.data.objects.remove(old_obj, do_unlink=True)

    old_pxy=get_obj_include("PivotXY")
    if (old_pxy):
        old_pxy.select_set(True)
        bpy.data.objects.remove(old_pxy, do_unlink=True)

    old_pz=get_obj_include("PivotZ")
    if (old_pz):
        old_pz.select_set(True)
        bpy.data.objects.remove(old_pz, do_unlink=True)

    #old_translate_pivot = get_obj_include('TranslateObj')
    #if(old_translate_pivot):
    #    bpy.ops.object.select_all(action='DESELECT')
    #    old_translate_pivot.select_set(True)
    #    bpy.data.objects.remove(old_translate_pivot, do_unlink=True)


def clear_all():
    print("deleting all content.... ")
    collections = bpy.data.collections 
    for collection in collections:
        for obj in collection.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection)


def clear_all_except_collection(except_collection):
    collections = bpy.data.collections 
    for collection in collections:
        for obj in collection.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        if(collection.name != except_collection):
            bpy.data.collections.remove(collection)

def reduce_size(org_obj,ratio=0.3,weight=30):
    
    reducedObjName='_'.join((org_obj.name,'r'))
    
    bpy.ops.object.select_all(action='DESELECT')
    try:
        bpy.data.objects[reducedObjName].select_set(True)
        bpy.ops.object.delete() 
    except:
        None
        
    reduced_obj = org_obj.copy()
    reduced_obj.data = org_obj.data.copy()
    reduced_obj.animation_data_clear()
    bpy.context.collection.objects.link(reduced_obj)
    
    reduced_obj.name=reducedObjName
    
    bpy.ops.object.select_all(action = 'DESELECT')
    reduced_obj.select_set(True)
    bpy.context.view_layer.objects.active = reduced_obj

    bpy.ops.object.modifier_add(type='DECIMATE')
    bpy.context.object.modifiers["Decimate"].ratio = ratio
    bpy.ops.object.modifier_apply(modifier="Decimate")

    bpy.ops.object.modifier_add(type='WEIGHTED_NORMAL')
    bpy.context.object.modifiers["WeightedNormal"].weight = weight
    bpy.ops.object.modifier_apply(modifier="WeightedNormal")

    # This is replacing the 'smothen_meshes' method
    #obj.data.use_auto_smooth = True
    return reduced_obj

def triangulate_object(obj):
    me = obj.data
    # Get a BMesh representation
    bm = bmesh.new()
    bm.from_mesh(me)

    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    # V2.79 : bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method=0, ngon_method=0)

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(me)
    bm.free()

def translate_point_by_obj(point,location,rotation):
    angle_x=rotation[0]
    rot_axis_x = [[ 1,  0,                  0                   ],
                  [ 0,  math.cos(angle_x),  -math.sin(angle_x)  ],
                  [ 0,  math.sin(angle_x),  -math.cos(angle_x)  ]]
    
    angle_y=rotation[1]
    rot_axis_y = [[ math.cos(angle_y),  0,  math.sin(angle_y)   ],
                  [ 0,                  1,  0                   ],
                  [ -math.sin(angle_y), 0,  math.cos(angle_y)   ]]

    #r = rot_axis_y @  rot_axis_x
    r=np.matmul(np.array(rot_axis_y), np.array(rot_axis_x))
    print(r)
    print(np.matmul(r,np.array(point)))


    return np.matmul(r,np.array(point))+location
