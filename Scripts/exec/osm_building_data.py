import os
import bpy
from  struct import *
import numpy as np

DTED_FOLDER_PATH = os.path.join(PROJECT_DIR,"Resources","DTED")
BUILDING_FOLDER_OUTPUT_PATH = os.path.join(PROJECT_DIR,"Resources","Buildings")
DEVIDER=6


def download_osm_files(lat,lon,dist):
    #bpy.context.scene.blosm.maxLat = lat+dist
    #bpy.context.scene.blosm.minLat = lat-dist
    #bpy.context.scene.blosm.maxLon = lon+dist
    #bpy.context.scene.blosm.minLon = lon-dist
    bpy.context.scene.blosm.maxLat = lat+dist
    bpy.context.scene.blosm.minLat = lat
    bpy.context.scene.blosm.maxLon = lon+dist
    bpy.context.scene.blosm.minLon = lon  
    

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



    #Select only bildings
    bpy.context.scene.blosm.water = False
    bpy.context.scene.blosm.forests = False
    bpy.context.scene.blosm.vegetation = False
    bpy.context.scene.blosm.highways = False
    bpy.context.scene.blosm.railways = False


    bpy.context.scene.blosm.buildings = True
    bpy.context.scene.blosm.ignoreGeoreferencing = True


    bpy.ops.blosm.import_data()



if os.path.exists(DTED_FOLDER_PATH):

    if not os.path.exists(BUILDING_FOLDER_OUTPUT_PATH):
        os.makedirs(BUILDING_FOLDER_OUTPUT_PATH)
        


    dted_files = os.listdir(DTED_FOLDER_PATH)
    dted_files = [dxt_file for dxt_file in dted_files if dxt_file.endswith('.dt1')]


    dted_reader=dted_ops.DTED(DTED_FOLDER_PATH)



    locationList = []
    desired_part=None
    desired_parts=[]

    for file_name in dted_files:
        locationList.append(geo_ops.GeoLocation(file_name))

        #if((locationList[-1].lat_trunc==39 or locationList[-1].lat_trunc==40) and (locationList[-1].lon_trunc==32 or locationList[-1].lon_trunc==33)):
        #    desired_parts.append(locationList[-1])
        if(locationList[-1].lat_trunc==40 and locationList[-1].lon_trunc==32):
            desired_parts.append(locationList[-1])
        #if(locationList[-1].lat_trunc==39 and locationList[-1].lon_trunc==32):
        #if(locationList[-1].lat_trunc==39 and locationList[-1].lon_trunc==33):
        #if(locationList[-1].lat_trunc==40 and locationList[-1].lon_trunc==33):
            #desired_part=locationList[-1]

    #filtered parts -> desired_parts
    for desired_part in desired_parts:

        on_earth_pos=geo_ops.lla2ecef(desired_part.lat_trunc,desired_part.lon_trunc,0)


        #Download desired part buildings
        #download_osm_files(locationList[0].lat_trunc,locationList[0].lon_trunc,1)

        for i in range(1):
            for j in range(1):
                i=0
                j=3

                desired_lat=desired_part.lat_trunc+(1/DEVIDER*i)
                desired_lon=desired_part.lon_trunc+(1/DEVIDER*j)

                #obj_ops.clear_all_except_collection("Collection")
                #download_osm_files(desired_lat,desired_lon,1/DEVIDER)

                #get downloaded buildings
                buildings_obj = obj_ops.get_obj_endswith('.osm_buildings')
            
                if(buildings_obj is None):
                    continue

                degree_length_of_longitude=geo_ops.degree_length_of_longitude(desired_part.lat_trunc)/2/6
                degree_length_of_latitude=geo_ops.degree_length_of_latitude(desired_part.lon_trunc)/2/6

                
                print(f"degree_length_of_longitude full 45: {geo_ops.degree_length_of_longitude(45)}  |   degree_length_of_latitude full 45: {geo_ops.degree_length_of_latitude(45)}")
                print(f"degree_length_of_longitude: {degree_length_of_longitude}  |   degree_length_of_latitude: {degree_length_of_latitude}")
                continue

                #print(len(buildings_obj.data.vertices))                

                building_export_data=[]

                building_export_data.append(pack('i',len(buildings_obj.data.vertices)))

                print(f"poly edges:  {len(buildings_obj.data.polygons[0].vertices)}")

                if(len(buildings_obj.data.polygons[0].vertices)!=3):
                    obj_ops.triangulate_object(buildings_obj)
                    print(f" triangulated...   {len(buildings_obj.data.polygons[0].vertices)}")

                print(f"vertex number:  {len(buildings_obj.data.vertices)}")
                for v in buildings_obj.data.vertices:

                    c1=dted_ops.GeoCoord(desired_part.c1)
                    c2=dted_ops.GeoCoord(desired_part.c2)
                    coords=(c1,c2)
                    height=dted_reader.get_height(coords,1,dted_ops.HeightQuery.NEAREST)
                    print(f"height: {height}")
                    building_export_data.append(pack('fff',v.co.x,v.co.z+height,v.co.y))

                for tris in buildings_obj.data.polygons:
                    for v_index in tris.vertices:            
                        building_export_data.append(pack('i',v_index))
                        #building_export_data.append(v_index.to_bytes(2,'little'))

                #export building data
                io_ops.export_bin_file(building_export_data,BUILDING_FOLDER_OUTPUT_PATH,f"{desired_part.lat_trunc}_{i+1}_{desired_part.lon_trunc}_{j+1}",".buildingdata")
                print(f"exported: {desired_part.lat_trunc}_{i+1}_{desired_part.lon_trunc}_{j+1}.buildingdata")
                print("      ")
