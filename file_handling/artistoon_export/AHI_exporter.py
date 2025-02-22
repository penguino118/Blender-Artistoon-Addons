import bpy
import math
import mathutils
from ..binary_rw import int16_write, int32_write, int32_write_signed, float_write, int32_write_list, pad_bytes
from ..sector_handler import get_sector_size


def get_parent(bone_list, bone): #incase it's none
    if bone.parent is not None:
        return bone_list.index(bone.parent)
    else:
        return -1

def get_child(bone_list, bone): #incase it's none
    if len(bone.children) > 0:
        return bone_list.index(bone.children[0]) # only one child per bone is allowed
    else:
        return -1

def get_type(bone): #incase it's none
    if len(bone.collections) > 0:
        return int(bone.collections[0].name) | 0x40000000
    else:
        print(f"Failed to get type for bone {bone.name} off bone collection, writing type 1 instead")
        return 0x40000001

def get_transform(bone, z_up, user_scale):
    shadow_scale = bone.get('shadow_scale')
    position, rotation, sca = bone.matrix_local.decompose()
    position = to_vector(position) * user_scale
    rotation = fixvector(rotation.to_euler('XYZ'))

    if bone.parent != None:
        parent_pos, parent_rot, parent_sca = bone.parent.matrix_local.decompose()
        parent_pos = to_vector(parent_pos) * user_scale
        parent_rot = fixvector(parent_rot.to_euler('XYZ'))
        position -= parent_pos
        rotation -= parent_rot
    
    if z_up:
        z_rotation = mathutils.Euler((math.radians(-90.0), 0.0, 0.0), 'XYZ')
        position.rotate(z_rotation)
        rotation.rotate(z_rotation)

    position = fixvector(position) # shitty 0.000000000000000000000000001 turn to 5.21512482149e-8502918012 values
    rotation = fixvector(rotation)

    transform = []
    transform.append(float_write(shadow_scale[0])) # scale (shadow mesh scale, not bone's)
    transform.append(float_write(shadow_scale[1])) 
    transform.append(float_write(shadow_scale[2]))
    transform.append(float_write(shadow_scale[3]))
    
    transform.append(float_write(rotation[0])) # rotation
    transform.append(float_write(rotation[1]))
    transform.append(float_write(rotation[2]))
    transform.append(float_write(1.0))
    
    transform.append(float_write(position[0])) # position
    transform.append(float_write(position[1]))
    transform.append(float_write(position[2]))
    transform.append(float_write(1.0))
    return transform

def to_vector(shit):
    return mathutils.Vector((shit[0], shit[1], shit[2]))

def fixvector(vectorA): # this sucks
    return mathutils.Vector((fuckoff(vectorA[0]), fuckoff(vectorA[1]), fuckoff(vectorA[2])))

def fuckoff(f1):
    #print(f"abs({f1}) < {0.00005} = {abs(f1) < 0.00005}")
    if abs(f1) < 0.00005:  # this SUCKS!!!!!!!!!!
        return 0.0
    else:
        return f1

def get_ahi(z_up, user_scale):
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
            boneID        = int32_write(bone_list.index(bone))
            bone_parent   = int32_write_signed(get_parent(bone_list, bone))
            bone_child    = int32_write_signed(get_child(bone_list, bone))
            bone_unknown1 = int32_write_signed(bone.get('bone_unknown1'))
            trans_inherit = int32_write_signed(bone.get('trans_inherit_mesh'))
            bone_type     = int32_write(get_type(bone))
            
            bone_transform = get_transform(bone, z_up, user_scale)
            
            # writing #
            
            bone_sector.append(bone_type) # bone miniheader
            bone_sector.append(int32_write(1))
            bone_sector.append(int32_write(0x10C)) # same size always expected
            
            bone_sector.append(boneID)
            bone_sector.append(bone_parent)
            bone_sector.append(bone_child)
            bone_sector.append(bone_unknown1)
            for float in bone_transform: bone_sector.append(float)
            bone_sector.append(trans_inherit)
            pad_bytes(bone_sector, 0x00, 0xBC)

        for thing in root_sector: finalbytes.append(thing)
        for thing in bone_sector: finalbytes.append(thing)
        finalbytes.insert(0, int32_write(0xC0000000)) #finalheader
        finalbytes.insert(1, int32_write(bone_count+1))
        finalbytes.insert(2, get_sector_size(finalbytes))   
        return finalbytes

def write(context, filepath, z_up, user_scale):
    print("Exporting Artistoon Armature...")
    ahi = get_ahi(z_up, user_scale)
    f = open(filepath, 'wb')
    for byte in ahi:
        f.write(byte)
    f.close()
    return {'FINISHED'}
