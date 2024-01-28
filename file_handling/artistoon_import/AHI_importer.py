import bpy
import array
import os
import mathutils
import math
#import struct
from ..sector_handler import AHI_sector_dict as sector_type_dict
from ..binary_rw import int16_read, int32_read, float_read

# sector_type_dict = {
    # 0xC0000000  : "AHI_magic",       #start of the file #count is global sector count
    # 0x00000000  : "AHI_tree_root",   #tree root model number (??)
    # 0x40000001  : "AHI_bone_type_1", #bone type 1
    # 0x40000002  : "AHI_bone_type_2", #bone type 1
    # }
    
# def read_file(filepath):
    # f = open(filepath, 'rb')
    # data = f.read()
    # f.close()
    # return data

# def int16_read(buf, offset):
    # return struct.unpack("<H", buf[offset:offset+2])[0]

# def int32_read(buf, offset):
    # return struct.unpack("<I", buf[offset:offset+4])[0]

# def float_read(buf, offset):
    # return struct.unpack("<f", buf[offset:offset+4])[0]

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

def get_bone(buf, offset, bone_count, bone_data, bone_matrix, type):
    bone_ID        = int32_read(buf, offset)
    bone_parent_ID = int32_read(buf, offset+0x4)
    bone_child_ID  = int32_read(buf, offset+0x8)
    bone_unk1 = int32_read(buf, offset+0xC)
    offset += 0x10
    scale    = ( float_read(buf, offset), float_read(buf, offset+0x4), float_read(buf, offset+0x8), float_read(buf, offset+0xC) )
    offset += 0x10
    rotation = ( float_read(buf, offset), float_read(buf, offset+0x4), float_read(buf, offset+0x8), float_read(buf, offset+0xC) )
    offset += 0x10
    position = ( float_read(buf, offset), float_read(buf, offset+0x4), float_read(buf, offset+0x8), float_read(buf, offset+0xC) )
    offset += 0x10
    bone_unk2 = int32_read(buf, offset)
    
    print(f"ID:{bone_ID}\nParent:{bone_parent_ID}\nChild:{bone_child_ID}\nunk1:{bone_unk1}\nunk2:{bone_unk2}")
    
    # create a location matrix
    mat_loc = mathutils.Matrix.Translation(position[:-1])
    # create an identitiy matrix
    mat_sca = mathutils.Matrix.Scale(1.0, 4, (1.0, 1.0, 1.0))
    # create a rotation matrix
    mat_rot = mathutils.Euler(rotation[:-1], 'XYZ').to_matrix()
    
    mat_out = mat_loc @ mat_rot.to_4x4() @ mat_sca
    if bone_parent_ID != 4294967295:
        mat_out += bone_matrix[bone_parent_ID]
    
    bone_data.append( [bone_ID, bone_parent_ID, bone_child_ID, bone_unk1, bone_unk2, type, scale] )
    bone_matrix.append(mat_out)
    #print(mat_out)
    

def build_armature(collection, filename, bone_count, root_bones, bone_data, bone_matrix, upflag):
    object_name = f"{filename}" 
    target_armature = bpy.data.armatures.new(object_name)
    target_armature.display_type = 'ENVELOPE'
    target_armature.show_names = True
    created_armature = bpy.data.objects.new(object_name, target_armature)
    collection.objects.link(created_armature)
    bpy.context.view_layer.objects.active = created_armature
    
    if len(root_bones) != 0:
        created_armature['root_bones'] = root_bones
    
    if upflag:
        created_armature.rotation_euler = (math.radians(90), 0.0, math.radians(180))
    
    for x in range(len(bone_matrix)):
        bpy.ops.object.mode_set(mode='EDIT')
        
        bone_name   = bone_data[x][0]
        bone_parent = bone_data[x][1]
        bone_child  = bone_data[x][2]
        bone_unk1   = bone_data[x][3]
        bone_mesh   = bone_data[x][4]
        bone_type   = bone_data[x][5]
        bone_scale  = bone_data[x][6]
        #print(bone_parent)
        bone = target_armature.edit_bones.new(str(bone_name))
        bone.parent = target_armature.edit_bones[str(bone_parent)] if bone_parent != 4294967295 else None
        bone.tail = mathutils.Vector((0, 0.0003, 0))
        bone.matrix = bone_matrix[x]
        
        bpy.ops.object.mode_set(mode='OBJECT')
        try:
            target_armature.bones.get(str(bone_name))['bone_type'] = bone_type  if bone_type  != 4294967295 else -1
            target_armature.bones.get(str(bone_name))['bone_child'] = bone_child if bone_child != 4294967295 else -1
            target_armature.bones.get(str(bone_name))['bone_unknown1'] = bone_unk1  if bone_unk1  != 4294967295 else -1
            target_armature.bones.get(str(bone_name))['trans_inherit_mesh'] = bone_mesh  if bone_mesh  != 4294967295 else -1
            target_armature.bones.get(str(bone_name))['bone_scale'] = bone_scale
        except:
            continue
            

def read_AHI(filedata, filepath, z_up):
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
            elif main_sector[0] == "AHI_bone_type_1":
                print_sector(main_sector)
                get_bone(filebuffer, read_offset+0xC, bone_count, bone_data, bone_matrix, 1)
                read_offset += main_sector[2]
            elif main_sector[0] == "AHI_bone_type_2":
                print_sector(main_sector)
                get_bone(filebuffer, read_offset+0xC, bone_count, bone_data, bone_matrix, 2)
                read_offset += main_sector[2]
            else:
                print_sector(main_sector)
        
        build_armature(collection, filename, bone_count, root_bones, bone_data, bone_matrix, z_up)

def read(context, filepath, z_up):
    print("running read_some_data...")
    f = open(filepath, 'rb')
    data = f.read()
    f.close()
    
    read_AHI(data, filepath, z_up)
    
    return {'FINISHED'}
