
import os
from struct import *



class Vert():

    def __init__(self, vertex):
        
        self.vert_x = vertex[0]
        self.vert_y = vertex[1]
        self.vert_z = vertex[2]

    def binary_data(self):
        return pack('fff',self.vert_x,self.vert_y,self.vert_z)

    #def write_binary(self, file_handle):

    #    file_handle.write(pack('f', self.vert_x))
    #    file_handle.write(pack('f', self.vert_y))
    #    file_handle.write(pack('f', self.vert_z))
        

def export_bin_file(data_list,output_dir,export_name,extention):
    io_path = os.path.join(output_dir, export_name + extention)
    with open(io_path, 'wb') as binary_file:
        for data in data_list:
            binary_file.write(data)

