import bpy
import array
import os
import mathutils
import math
#import struct
from ..sector_handler import AHI_sector_dict as sector_type_dict
from ..binary_rw import int16_read, int32_read, int32_read_signed, float_read


def get_sector_type(buffer, offset):
    head = int32_read(buffer, offset)
    if head in sector_type_dict:
        return sector_type_dict[head]
    else:
        return f"unsupported sector : {head} at offset {offset}"

def get_sector_header(buffer, offset):
    head = get_sector_type(buffer, offset)
    count = int32_read(buffer, offset+4)
    size = int32_read(buffer, offset+8)
    return [head, count, size]

def print_sector(sector):
    if len(sector) < 3:
        print("invalid sector!! size under 3")
    print(f"Sector Type: {sector[0]}, Data Count: {sector[1]}, Size: {sector[2]}")

def get_tree_root_bones(buf, offset, bone_count, list):
    for x in range(bone_count):
        root_bone = int32_read(buf, offset)
        list.append(root_bone)
        offset += 0x4

def get_bone(buf, offset, bone_count, bone_data, bone_matrix, type, z_up, user_scale):
    bone_ID        = int32_read_signed(buf, offset)
    bone_parent_ID = int32_read_signed(buf, offset+0x4)
    bone_child_ID  = int32_read_signed(buf, offset+0x8)
    bone_unk1 = int32_read_signed(buf, offset+0xC)
    
    offset += 0x10
    shadow_scale = mathutils.Vector((float_read(buf, offset), float_read(buf, offset+0x4), float_read(buf, offset+0x8), float_read(buf, offset+0xC)))
    print(f"Shadow Scale: {shadow_scale}")
    offset += 0x10
    rotation = mathutils.Vector((float_read(buf, offset), float_read(buf, offset+0x4), float_read(buf, offset+0x8), float_read(buf, offset+0xC)))
    
    offset += 0x10
    position = mathutils.Vector((float_read(buf, offset), float_read(buf, offset+0x4), float_read(buf, offset+0x8), float_read(buf, offset+0xC)))*user_scale
    
    offset += 0x10
    bone_mesh = int32_read_signed(buf, offset)
    
    if z_up:
        z_rotation = mathutils.Euler((math.radians(90.0), 0.0, 0.0), 'XYZ')
        position.rotate(z_rotation)
        rotation.rotate(z_rotation)
        # should maybe rotate shadow scale too
    
    print(f"ID:{bone_ID}\nParent:{bone_parent_ID}\nChild:{bone_child_ID}\nunk1:{bone_unk1}\nMesh:{bone_mesh}\nType:{type}")
    print(f"Shadow Scale: {shadow_scale}")
    
    mat_loc = mathutils.Matrix.Translation(position[:-1])
    mat_sca = mathutils.Matrix.Scale(1.0, 4, (1.0, 1.0, 1.0))
    mat_rot = mathutils.Euler(rotation[0:3], 'XYZ').to_matrix()
    
    matrix = mat_loc @ mat_rot.to_4x4() @ mat_sca
    
    if bone_parent_ID != -1:
        matrix += bone_matrix[bone_parent_ID]
    
    bone_data.append([bone_ID, bone_parent_ID, bone_child_ID, bone_unk1, bone_mesh, type, shadow_scale])
    bone_matrix.append(matrix)
    #print(mat_out)
    

def build_armature(collection, filename, bone_count, root_bones, bone_data, bone_matrix):
    def get_collecton(armature, type):
        for collection in armature.collections_all:
            if collection.name == str(type): # check if collection exists already
                return collection
        return armature.collections.new(str(type)) # create if collection doesnt exist
    
    object_name = f"{filename}" 
    target_armature = bpy.data.armatures.new(object_name)
    target_armature.display_type = 'STICK'
    target_armature.show_names = True
    created_armature = bpy.data.objects.new(object_name, target_armature)
    collection.objects.link(created_armature)
    bpy.context.view_layer.objects.active = created_armature
    
    if len(root_bones) > 0:
        created_armature['root_bones'] = root_bones
    
    for x in range(len(bone_matrix)):
        bpy.ops.object.mode_set(mode='EDIT')
        
        bone_id   = bone_data[x][0]
        bone_unk1   = bone_data[x][3]
        bone_mesh   = bone_data[x][4]
        bone_type   = bone_data[x][5]
        shadow_scale  = bone_data[x][6]
        bone = target_armature.edit_bones.new(str(bone_id))
        bone.tail = mathutils.Vector((0, 0.0003, 0))
        bone.matrix = bone_matrix[x]
        
        bone_collection = get_collecton(target_armature, bone_type)
        bone_collection.assign(bone)
        
        # custom properties
        bpy.ops.object.mode_set(mode='OBJECT')
        target_armature.bones.get(str(bone_id))['bone_type'] = bone_type
        target_armature.bones.get(str(bone_id))['bone_unknown1'] = bone_unk1
        target_armature.bones.get(str(bone_id))['trans_inherit_mesh'] = bone_mesh
        target_armature.bones.get(str(bone_id))['shadow_scale'] = shadow_scale
    
    bpy.ops.object.mode_set(mode='EDIT')
    for x in range(len(bone_matrix)): # set up bone relationships after they're all created_armature
        bone_id   = bone_data[x][0]
        bone_parent_id = bone_data[x][1]
        bone_child_id  = bone_data[x][2]
        try:
            bone = target_armature.edit_bones.get(str(bone_id))
            if bone_parent_id != -1:
                bone.parent = target_armature.edit_bones.get(str(bone_parent_id)) 
            if bone_child_id != -1:
                child = target_armature.edit_bones.get(str(bone_child_id))
                child.parent = bone
        except:
            print(f"something went wrong idk {bone_id} {bone_parent_id} {bone_child_id}")
    bpy.ops.object.mode_set(mode='OBJECT')


def read_AHI(filedata, filepath, user_scale, z_up):
    filebuffer = filedata
    filename = os.path.basename(filepath)
    read_offset = 0
    sector = get_sector_header(filebuffer, read_offset)
    if sector[0] != "AHI_magic":
        print(f"magic sect missing 0x0\n{sector[0]}")
        return
    else:
        collection_name = f"{filename[:-4]}"
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
        
        sector_count = sector[1]
        read_offset += 0xC
        
        bone_count = sector_count - 1
        root_bones = []
        bone_data = []
        bone_matrix = []
        
        for x in range(sector_count):
            main_sector = get_sector_header(filebuffer, read_offset)
            if main_sector[0] == "AHI_tree_root":
                get_tree_root_bones(filebuffer, read_offset+0xC, main_sector[1], root_bones)
                print_sector(main_sector)
                read_offset += main_sector[2]
            elif main_sector[0] == "AHI_bone_type_1" or main_sector[0] == "AHI_bone_type_2":
                bone_type = int32_read(filebuffer, read_offset) ^ 0x40000000
                get_bone(filebuffer, read_offset+0xC, bone_count, bone_data, bone_matrix, bone_type, z_up, user_scale)
                print_sector(main_sector)
                read_offset += main_sector[2]
            else:
                print(f"UNKNOWN: {print_sector(main_sector)}")
        
        build_armature(collection, filename, bone_count, root_bones, bone_data, bone_matrix)


def read(context, filepath, user_scale, z_up):
    f = open(filepath, 'rb')
    data = f.read()
    f.close()
    read_AHI(data, filepath, user_scale, z_up)
    return {'FINISHED'}
