import bpy
import array
import os
import mathutils
import math
#import struct
from ..sector_handler import get_sector_info, AHI_sector_dict as sector_type_dict
from ..binary_rw import int16_read, int32_read, int32_read_signed, float_read

z_up_rotation = mathutils.Euler((math.radians(90.0), 0.0, math.radians(180.0)), 'XYZ')

# to properly sort children names
# https://stackoverflow.com/questions/58861558/natural-sorting-of-a-list-in-python3

import re

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

##################################################################################

def get_tree_root_bones(buffer, offset, bone_count, list):
    for x in range(bone_count):
        root_bone = int32_read(buffer, offset)
        list.append(root_bone)
        offset += 0x4


def get_bone_data(buffer, offset, user_scale):
    return {
        "type"    : int32_read(buffer, offset) ^ 0x40000000,
        "index"   : int32_read_signed(buffer, offset+0xC),
        "parent"  : int32_read_signed(buffer, offset+0x10),
        "child"   : int32_read_signed(buffer, offset+0x14),
        "brother" : int32_read_signed(buffer, offset+0x18),
        "scale" : mathutils.Vector((float_read(buffer, offset+0x1C)*user_scale, 
                                    float_read(buffer, offset+0x20)*user_scale, 
                                    float_read(buffer, offset+0x24)*user_scale, 
                                    float_read(buffer, offset+0x28)*user_scale)),
        "rotation" : mathutils.Vector((math.degrees(float_read(buffer, offset+0x2C)),
                                       math.degrees(float_read(buffer, offset+0x30)),
                                       math.degrees(float_read(buffer, offset+0x34)))),
        "position" : mathutils.Vector((float_read(buffer, offset+0x3C)*user_scale,
                                       float_read(buffer, offset+0x40)*user_scale,
                                       float_read(buffer, offset+0x44)*user_scale,
                                       float_read(buffer, offset+0x48)*user_scale)),
        "attached_mesh_index" : int32_read_signed(buffer, offset+0x4C),
    }
    

def build_armature(filename, bone_data_list, root_bone_list, mesh_objects):

    def set_bone_relationship(target_armature, bone_data):
        try:
            bone = target_armature.edit_bones.get(str(bone_data["index"]))
            if bone_data["parent"] != -1:
                parent_bone = target_armature.edit_bones.get(str(bone_data["parent"])) 
                bone.parent = parent_bone
            if bone_data["child"] != -1:
                child = target_armature.edit_bones.get(str(bone_data["child"]))
                child.parent = bone
            if bone_data["brother"] != -1:
                parent_bone = target_armature.edit_bones.get(str(bone_data["parent"])) 
                brother_bone = target_armature.edit_bones.get(str(bone_data["brother"]))
                brother_bone.parent = parent_bone
        except:
            print(f"Error setting bone {bone_data_list.index(bone_data)} relationships:")
            b = bone_data["index"]
            p = bone_data["parent"]
            c = bone_data["child"]
            r = bone_data["brother"]
            print(f"- bone_id={b}; parent={p}; child={c}; brother={r};")
    
    def get_matrix(bone_data):
        position = bone_data["position"]
        print(bone_data["rotation"])
        print("-  ", bone_data["rotation"])
        rotation = mathutils.Euler(bone_data["rotation"], 'XYZ') 
        print("+  ", rotation)
        scale = mathutils.Vector((1.0, 1.0, 1.0))
        return mathutils.Matrix.LocRotScale(position[0:3], rotation, scale)

    def get_collecton(armature, type):
        collection_name = f"Type {str(type)}"
        for collection in armature.collections_all:
            if collection.name == collection_name: # check if collection exists already
                return collection
        return armature.collections.new(collection_name) # create if collection doesnt exist
    
    armature_name = f"{filename[:-4]}_AHI" 
    target_armature = bpy.data.armatures.new(armature_name)
    created_armature = bpy.data.objects.new(armature_name, target_armature)
    
    bpy.context.scene.collection.objects.link(created_armature)
    bpy.context.view_layer.objects.active = created_armature
    
    for mesh in mesh_objects:
        mesh.parent = created_armature

    target_armature.display_type = 'STICK'
    target_armature.show_names = True
    
    if len(root_bone_list) > 0:
        created_armature['root_bones'] = root_bone_list
    
    # create bones
    bpy.ops.object.mode_set(mode='EDIT')
    for bone_data in bone_data_list:
        bone = target_armature.edit_bones.new(str(bone_data["index"]))
        bone.tail = mathutils.Vector((0, 0.0003, 0))

        # bone collection for different types
        # not the best way of doing this
        bone["champagne wishes"] = bone_data["attached_mesh_index"]
        bone_collection = get_collecton(target_armature, bone_data["type"])
        bone_collection.assign(bone)
        

        bone.matrix = get_matrix(bone_data) # set transformation matrix
        
        if bone_data_list.index(bone_data) == 20:
            print(bone.matrix)
        # todo: add scale property somewhere
    
    for bone_data in bone_data_list:
        if (bone_data["parent"] != -1): # transform by it's parent if it exists
            bone = target_armature.edit_bones.get(str(bone_data["index"])) 
            parent_bone = target_armature.edit_bones.get(str(bone_data["parent"])) 
            try:
                bone.matrix += parent_bone.matrix
            except:
                print(f"invalid: edit_bone={bone}, target_armature.edit_bones.get({str(bone_data['index'])})")
                print(f"invalid: parent_bone={parent_bone}, target_armature.edit_bones.get({str(bone_data['parent'])})")
                continue

    # set relations and such
    for bone_data in bone_data_list:
        set_bone_relationship(target_armature, bone_data)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    sorted_children = sorted(created_armature.children[:], key=lambda obj: natural_keys(obj.name))
    for s in sorted_children:
        print(s.name)
    
    for bone_data in bone_data_list:
        try:
            bone_id = bone_data["index"]
            mesh_index = bone_data["attached_mesh_index"]
            bone = target_armature.bones.get(str(bone_id))
            

            if mesh_index != -1: 
                sorted_children[mesh_index].location = mathutils.Vector((0.0, 0.0, 0.0))
                sorted_children[mesh_index].parent_type = 'BONE'
                sorted_children[mesh_index].parent_bone = bone.name
        except:
            print(f"Error parenting mesh to bone {bone_data_list.index(bone_data)}")
    
    


def ahi_read(filebuffer, filepath, mesh_objects, use_z_up, user_scale):
    filename = os.path.basename(filepath)
    bone_data_list = []
    root_bone_list = []
    read_offset = 0x0
    magic_sector = get_sector_info(filebuffer, read_offset)

    if magic_sector["header"] != sector_type_dict["Magic"]:
        print("Magic sector missing from skeleton file.")
        return
    read_offset += 0xC # skip over the header
    
    for x in range(magic_sector["data_count"]):
        current_sector = get_sector_info(filebuffer, read_offset)

        if (current_sector["header"] & 0x40000000) == sector_type_dict["BoneNode"]:
            bone_data = get_bone_data(filebuffer, read_offset, user_scale)
            if use_z_up:
                bone_data["scale"].rotate(z_up_rotation)
                print("pre=", bone_data["rotation"])
                bone_data["rotation"].rotate(z_up_rotation)
                print("pos=", bone_data["rotation"])
                bone_data["position"].rotate(z_up_rotation)
            bone_data_list.append(bone_data)

        read_offset += current_sector["data_size"]

    build_armature(filename, bone_data_list, root_bone_list, mesh_objects)


def read(context, filepath, user_scale, use_z_up):
    f = open(filepath, 'rb')
    data = f.read()
    f.close()

    return {'FINISHED'}
