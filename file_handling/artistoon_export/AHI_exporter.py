import bpy
import math
import mathutils
from ..util import flip_yz
from collections import defaultdict
from ..binary_rw import int32_write_signed, float_write, pad_with_byte
from ..sector_handler import insert_header


def get_ordered_bone_list(armature_obj):
    armature = armature_obj.data
    ordered_bones_info = []
    bone_name_to_index = {} # map bone name to its index in the final list

    def process_bone(bone, parent_index):
        current_index = len(ordered_bones_info)
        bone_name_to_index[bone.name] = current_index
        bone_info = {
            'name': bone.name,
            'parent': parent_index,
            'child': None,
            'sibling': None 
        }
        ordered_bones_info.append(bone_info)

        # get children
        children = bone.children
        last_child_index = None
        for i, child_bone in enumerate(children):
            process_bone(child_bone, current_index)
            child_index = bone_name_to_index[child_bone.name]
            if i == 0:
                # if this is the first child, set the parent's "child" field
                ordered_bones_info[current_index]['child'] = child_index
            else:
                # if this is not the first child, set the previous child's "sibling" field
                if last_child_index is not None:
                    ordered_bones_info[last_child_index]['sibling'] = child_index
            
            # update the index of the last processed child
            last_child_index = child_index

    # find root bones (bones with no parent)
    root_bones = [bone for bone in armature.bones if not bone.parent]
    
    if not root_bones and len(armature.bones) > 0:
        # shouldn't happen in a proper armature.
        print(f"Warning: Armature has bones but no root bones. ({armature.name})")
        processed_names = set()
        for bone in armature.bones:
           if bone.name not in processed_names:
               # find its true parent index if already processed
               parent_idx = None
               if bone.parent and bone.parent.name in bone_name_to_index:
                   parent_idx = bone_name_to_index[bone.parent.name]
               process_bone(bone, parent_idx) # todo: ehhh?
               processed_names.add(bone.name)
    
    elif root_bones:
        last_root_bone_index = None
        for i, root_bone in enumerate(root_bones):
            process_bone(root_bone, None) # roots have no parent
            current_root_index = bone_name_to_index[root_bone.name]
            if i > 0:
                # link the previous root bone to this one as a sibling
                if last_root_bone_index is not None:
                   ordered_bones_info[last_root_bone_index]['sibling'] = current_root_index
            # update the index of the last processed root bone
            last_root_bone_index = current_root_index

    return ordered_bones_info


def get_transform(armature_object, bone_name, z_up, user_scale):
    bone = armature_object.data.bones[bone_name]
    shadow_volume_size = bone.AHI_ShadowVolumeSize
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
        flip_yz(position)
        flip_yz(rotation)

    position = fixvector(position) # shitty 0.000000000000000000000000001 turn to 5.21512482149e-8502918012 values
    rotation = fixvector(rotation)

    transform = bytearray()

    for float in shadow_volume_size:
        transform.extend(float_write(float))
    
    for float in rotation:
        transform.extend(float_write(float))
    transform.extend(float_write(1.0))
    
    for float in position:
        transform.extend(float_write(float))
    transform.extend(float_write(1.0))
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


def get_attached_mesh(armature, bone, mesh_objects):
    if mesh_objects == None: return -1
    
    for i, obj in enumerate(mesh_objects): # check if the object is a mesh and is parented to the bone
        if obj.parent == armature and obj.parent_type == 'BONE' and obj.parent_bone == bone["name"]:
            return i
    
    return -1


def get_ahi(armature_object, use_z_up, user_scale, mesh_objects = None):
    output_bytes = bytearray()
    bone_list = []
    entry_info = {
        "index" : armature_object.PZZ_Index,
        "compressed" : armature_object.PZZ_Compressed
        }
    
    if armature_object.type == 'ARMATURE':
        print("Exporting AHI from Armature: ", armature_object.name)
        root_bones = [bone for bone in armature_object.data.bones if bone.parent is None]
        bone_list = get_ordered_bone_list(armature_object)
        
        # root bone list
        # there's probably a better way of doing this
        root_list_bytes = bytearray()
        for root_bone in root_bones:
            for i, bone in enumerate(bone_list):
                if bone["name"] == root_bone.name:
                    root_list_bytes.extend(int32_write_signed(i))
        insert_header(root_list_bytes, 0x0, len(root_bones))

        # main bone list
        bone_list_bytes = bytearray()
        for i, bone in enumerate(bone_list):
            bone_bytes = bytearray()

            # gather data
            bone_id = i
            bone_child = bone["child"] if bone["child"] != None else -1
            bone_parent = bone["parent"] if bone["parent"] != None else -1
            bone_sibling = bone["sibling"]  if bone["sibling"] != None else -1
            bone_mesh = get_attached_mesh(armature_object, bone, mesh_objects)
            bone_type = 1 + (bone_mesh != -1) | 0x40000000 # todo: double check if auto modellista follows this logic too
            bone_transform = get_transform(armature_object, bone["name"], use_z_up, user_scale)

            # write
            bone_bytes.extend(int32_write_signed(bone_id))
            bone_bytes.extend(int32_write_signed(bone_parent))
            bone_bytes.extend(int32_write_signed(bone_child))
            bone_bytes.extend(int32_write_signed(bone_sibling))
            bone_bytes.extend(bone_transform)
            bone_bytes.extend(int32_write_signed(bone_mesh))
            pad_with_byte(bone_bytes, 0x00, 0xBC)
            insert_header(bone_bytes, bone_type, 1)
            bone_list_bytes.extend(bone_bytes)
        
        output_bytes.extend(root_list_bytes)
        output_bytes.extend(bone_list_bytes)
        
        # count total sector count for all bones + the list of root bones 
        insert_header(output_bytes, 0xC0000000, len(bone_list)+1)
    
    return output_bytes, entry_info, bone_list