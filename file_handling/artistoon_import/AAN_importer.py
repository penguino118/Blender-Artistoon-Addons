import bpy
import os 
from ..sector_handler import AAN_sector_dict as sector_type_dict
from ..binary_rw import int08_read, int16_read, int16_read_signed, int32_read, float_read


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


def get_keyframe(buffer, offset, type, action):
    if type == 1:
        value    = float_read(buffer, offset)
        frame    = float_read(buffer, offset+0x4)
        ease_in  = float_read(buffer, offset+0x8)
        ease_out = float_read(buffer, offset+0xC)
        if frame > action.frame_end:
            action.frame_end = frame
        return [value, frame, ease_in, ease_out]
    elif type == 2:
        value    = float(int16_read_signed(buffer, offset) / 2607.5946)    
        frame    = int16_read_signed(buffer, offset+0x2)
        ease_in  = float(int16_read_signed(buffer, offset+0x4) / 2607.5946)
        ease_out = float(int16_read_signed(buffer, offset+0x6) / 2607.5946)
        if frame > action.frame_end:
            action.frame_end = frame
        return [value, frame, ease_in, ease_out]

def set_dummy_keyframe(armature, anim_name, anim_index, index):
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = bpy.data.actions[anim_name]
    bone = armature.pose.bones[str(index)]
    bone.keyframe_insert('location', index=0, frame=-1.234)
    bone.keyframe_insert('location', index=1, frame=-1.234)
    bone.keyframe_insert('location', index=2, frame=-1.234)
    
def set_keyframe(armature, anim_name, type, anim_index, axis, index, keyframe_list):
    if not armature.animation_data:
        armature.animation_data_create()
    
    armature.animation_data.action = bpy.data.actions[anim_name]
    bone = armature.pose.bones[str(index)]

    for keyframe in keyframe_list:
        anim_value    = keyframe[0]
        anim_frame    = keyframe[1]
        anim_ease_in  = keyframe[2]
        anim_ease_out = keyframe[3]

        if type == "translation":
            bone.location[axis] = anim_value
            bone.keyframe_insert('location', index=axis, frame=anim_frame)
        elif type == "rotation":
            bone.rotation_mode = 'XYZ'
            bone.rotation_euler[axis] = anim_value# * (57.33/2)
            bone.keyframe_insert('rotation_euler', index=axis, frame=anim_frame)

def read_aan(data, path):
    filebuffer = data
    filename = os.path.basename(path)
    
    armature = bpy.context.active_object
    
    read_offset = 0
    header_offset = 0
    animation_count = 0
    header_size = int32_read(filebuffer, 0xC)
    
    test_offset = int32_read(filebuffer, 0x4)
    header_size = int32_read(filebuffer, test_offset)
    
    if int32_read(filebuffer, test_offset-0x28) != 0:
        animation_count = int32_read(filebuffer, test_offset-0x28)
    else:
        animation_count = int32_read(filebuffer, 0x0)
    
    read_offset += header_size
    
    #create collection and empty
    collection_name = f"{filename[:-4]}"
    collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(collection)
    
    obj_name = f"{filename[:-4]}_animations"
    
    target_obj = bpy.data.meshes.new(obj_name)
    created_obj = bpy.data.objects.new(obj_name, target_obj)
    collection.objects.link(created_obj)
    
    action_array = []
    
    for a in range(animation_count):
        animation_name = f"{filename}_act_{a}"
        action_array.append(animation_name)
        
        bpy.data.actions.new(name=animation_name)
        current_action = bpy.data.actions[animation_name]
        
        container = get_sector_header(filebuffer, read_offset)
        block_type = int08_read(filebuffer, read_offset)
        total_sectors = container[1]
        read_offset += 0xC
        loop_flag = int32_read(filebuffer, read_offset)
        loop_start = float_read(filebuffer, read_offset+0x4)
        
        current_action.use_frame_range = True
        if loop_flag == 1:
            current_action.use_cyclic = True
            current_action.frame_start = loop_start
        
        read_offset += 0x8
        for b in range(total_sectors):
            print(b, read_offset)
            main_sector = get_sector_header(filebuffer, read_offset)
            
            if main_sector[0] == "ProbablyImportant":
                print_sector(main_sector)
                set_dummy_keyframe(armature, animation_name, a, b)
                read_offset += main_sector[2]
            
            elif main_sector[0] == "TranslationBlock":
                print_sector(main_sector)
                read_offset += 0xC
                count = main_sector[1]
                for c in range(count):
                    animation = get_sector_header(filebuffer, read_offset)
                    read_offset += 0xC
                    print_sector(animation)
                    frame_count = animation[1]
                    keyframes = []
                    for d in range(frame_count):
                        keyframes.append(get_keyframe(filebuffer, read_offset, block_type, current_action))
                        
                        if block_type == 1:
                            read_offset += 0x10
                        else:
                            read_offset += 0x8
                    set_keyframe(armature, animation_name, "translation", a, c, b, keyframes)
        
            elif main_sector[0] == "RotationBlock":
                print_sector(main_sector)
                read_offset += 0xC
                count = main_sector[1]
                for c in range(count):
                    animation = get_sector_header(filebuffer, read_offset)
                    read_offset += 0xC
                    print_sector(animation)
                    frame_count = animation[1]
                    keyframes = []
                    for d in range(frame_count):
                        keyframes.append(get_keyframe(filebuffer, read_offset, block_type, current_action))
                        #set_keyframe(armature, "translation", c, b, keyframe)
                        if block_type == 1:
                            read_offset += 0x10
                        else:
                            read_offset += 0x8
                    set_keyframe(armature, animation_name, "rotation", a, c, b, keyframes)
            else:
                print(main_sector[0])
                read_offset += main_sector[2]
    
    created_obj.data[f'actions'] = action_array
                
def read(context, filepath):
    print("running read_some_data...")
    f = open(filepath, 'rb')
    data = f.read()
    f.close()
    read_aan(data, filepath)
    return {'FINISHED'}
