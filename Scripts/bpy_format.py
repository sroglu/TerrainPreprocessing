import bpy
import os
import imp

# -----------------------------------------------------------------------------
# Settings
SCRIPTS_PATH ="scripts"
BLENDER_DIR = os.path.dirname(os.path.dirname(__file__))

# -----------------------------------------------------------------------------
# Methods
def import_script(script_name):
    file_path = os.path.join(BLENDER_DIR,SCRIPTS_PATH,"lib",script_name)
    script_path=bpy.path.abspath(file_path)
    return imp.load_source(script_name, script_path)

def get_executable_script(script_name):
    file_path = os.path.join(BLENDER_DIR,SCRIPTS_PATH,"exec",script_name)
    script_path=bpy.path.abspath(file_path)
    return compile(open(script_path).read(), script_path, 'exec')


# -----------------------------------------------------------------------------
# Lib Scripts
obj_ops=import_script("obj_ops.py")
#geo_ops=import_script("geo_ops.py")
#io_ops=import_script("io_ops.py")
dted_ops=import_script("dted_ops_v2.py")

# -----------------------------------------------------------------------------
# Executable Scripts
#osm_get_tree_exe = get_executable_script("osm_forest_data.py")
#osm_get_buildings_exe = get_executable_script("osm_building_data.py")
dted_test_exe = get_executable_script("dted_test.py")


# -----------------------------------------------------------------------------
# Scripts

obj_ops.clear_all_except_collection("Collection")
exec(dted_test_exe)
#obj_ops.clear_all_except_collection("Collection")