import bpy
import struct
import os

sector_type_dict = {
    0x80000001  : "AnimationBlock01",
    0x80000002  : "AnimationBlock02",
    0x0000000C  : "ProbablyImportant",
    0x800001C0  : "TranslationBlock",
    0x80220040  : "TranslationX",
    0x80220080  : "TranslationY",
    0x80220100  : "TranslationZ",
    0x80120040  : "TransShortX",
    0x80120080  : "TransShortY",
    0x80120100  : "TransShortZ",
    0x80000038  : "RotationBlock",
    0x80220008  : "RotationX",
    0x80220010  : "RotationY",
    0x80220020  : "RotationZ",
    0x80120008  : "RotaShortX",
    0x80120010  : "RotaShortY",
    0x80120020  : "RotaShortZ",
    }
    
def int08_read(buf, offset):
    return struct.unpack("<B", buf[offset:offset+1])[0]

def int16_read(buf, offset):
    return struct.unpack("<H", buf[offset:offset+2])[0]

def signed_int16_read(buf, offset):
    return struct.unpack("<h", buf[offset:offset+2])[0]

def int32_read(buf, offset):
    return struct.unpack("<I", buf[offset:offset+4])[0]

def float_read(buf, offset):
    return struct.unpack("<f", buf[offset:offset+4])[0]

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
        value    = float(signed_int16_read(buffer, offset) / 2607.5946)    
        frame    = signed_int16_read(buffer, offset+0x2)
        ease_in  = float(signed_int16_read(buffer, offset+0x4) / 2607.5946)
        ease_out = float(signed_int16_read(buffer, offset+0x6) / 2607.5946)
        if frame > action.frame_end:
            action.frame_end = frame
        return [value, frame, ease_in, ease_out]


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


def read_ahi(data, path):
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
    
    for a in range(animation_count):
        animation_name = f"{filename}_act_{a}"
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
            main_sector = get_sector_header(filebuffer, read_offset)
            
            if main_sector[0] == "ProbablyImportant":
                print_sector(main_sector)
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
                read_offset += main_sector[2]
                

def read_some_data(context, filepath):
    print("running read_some_data...")
    f = open(filepath, 'rb')
    data = f.read()
    f.close()

    read_ahi(data, filepath)

    return {'FINISHED'}

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class Import_AAN(Operator, ImportHelper):
    """Import Artistoon Animation data to the currently selected armature."""
    bl_idname = "import_scene.aan"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Artistoon Animation"

    # ImportHelper mixin class uses this
    filename_ext = ".aan/.bin"

    filter_glob: StringProperty(
        default="*.aan;*.bin",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
#    use_setting: BoolProperty(
#        name="Example Boolean",
#        description="Example Tooltip",
#        default=True,
#    )

#    type: EnumProperty(
#        name="Example Enum",
#        description="Choose between two items",
#        items=(
#            ('OPT_A', "First Option", "Description one"),
#            ('OPT_B', "Second Option", "Description two"),
#        ),
#        default='OPT_A',
#    )

    def execute(self, context):
        return read_some_data(context, self.filepath)


# Only needed if you want to add into a dynamic menu.
def menu_func_import(self, context):
    self.layout.operator(Import_AAN.bl_idname, text="Artistoon Animation (.aan | .bin)")


# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access).
def register():
    bpy.utils.register_class(Import_AAN)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(Import_AAN)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_scene.aan('INVOKE_DEFAULT')
