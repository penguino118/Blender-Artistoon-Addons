import bpy
import math
import mathutils
from ..binary_rw import int16_write, int32_write, int32_write_signed, float_write, int32_write_list, pad_bytes
from ..sector_handler import get_sector_size


def handle_parent(bone_list, bone_parent): #incase it's none
    if bone_parent is not None:
        return bone_list.index(bone_parent)
    else:
        return -1

def to_vector(shit):
    return mathutils.Vector((shit[0], shit[1], shit[2]))

def get_ahi():
    object = bpy.context.active_object
    if object.type == 'ARMATURE':
        finalbytes = []
        root_sector = []
        bone_sector = []
        
        bones = object.data.bones
        bone_count = len(object.data.bones)
        root_bones = object.get('root_bones')
        bone_list = list(bones)

        root_sector.append(int32_write(0x00000000))
        root_sector.append(int32_write(len(root_bones)))
        root_sector.append(int32_write((len(root_bones) * 4) + 0xC))
        
        for bone in root_bones:
            root_sector.append(int32_write(bone))

        for bone in bones:
            boneID = int32_write(bone_list.index(bone))
            bone_parent = int32_write_signed(handle_parent(bone_list, bone.parent))
            bone_child =    int32_write_signed(bone.get('bone_child'))
            bone_unknown1 = int32_write_signed(bone.get('bone_unknown1'))
            trans_inherit = int32_write_signed(bone.get('trans_inherit_mesh'))
            bone_type =     int32_write(bone.get('bone_type') + 0x40000000)
            bone_scale = bone.get('bone_scale')
        
            loc, rot, sca = bone.matrix_local.decompose()
            rot = to_vector(rot.to_euler('XYZ')) #[mathutils.Vector (val) for val in rot.to_euler('XYZ')] # list(rot.to_euler('XYZ'))

            if bone.parent != None:
                parent_loc, parent_rot, parent_sca = bone.parent.matrix_local.decompose()
                parent_rot = to_vector(parent_rot.to_euler('XYZ'))
                loc -= parent_loc
                rot -= parent_rot
                sca -= parent_sca

            transform = []
            transform.append(float_write(bone_scale[0])) #scale 
            transform.append(float_write(bone_scale[1])) 
            transform.append(float_write(bone_scale[2]))
            transform.append(float_write(bone_scale[3])) 
            
            transform.append(float_write(rot[0])) # rotation
            transform.append(float_write(rot[1]))
            transform.append(float_write(rot[2]))
            transform.append(float_write(1.0))
            
            transform.append(float_write(loc[0])) # position
            transform.append(float_write(loc[1]))
            transform.append(float_write(loc[2]))
            transform.append(float_write(1.0))
            
            # writing #
            
            bone_sector.append(bone_type) # bone miniheader
            bone_sector.append(int32_write(1))
            bone_sector.append(int32_write(0x10C)) # same size always expected
            
            bone_sector.append(boneID)
            bone_sector.append(bone_parent)
            bone_sector.append(bone_child)
            bone_sector.append(bone_unknown1)
            for float in transform: bone_sector.append(float)
            bone_sector.append(trans_inherit)
            pad_bytes(bone_sector, 0x00, 0xBC)

        for thing in root_sector: finalbytes.append(thing)
        for thing in bone_sector: finalbytes.append(thing)
        finalbytes.insert(0, int32_write(0xC0000000)) #finalheader
        finalbytes.insert(1, int32_write(bone_count+1))
        finalbytes.insert(2, get_sector_size(finalbytes))   
        return finalbytes

def write(context, filepath):
    print("Exporting Artistoon Armature...")
    ahi = get_ahi()
    f = open(filepath, 'wb')
    for byte in ahi:
        f.write(byte)
    f.close()
    return {'FINISHED'}
