import bpy
import struct

bl_info = {
    "name": "Artistoon Armature Exporter",
    "description": "Exporter for the Artistoon Armature Format (AHI) found in GioGio's Bizarre Adventure.",
    "author": "Penguino",
    "version": (1, 0),
    "blender": (3, 6, 1),
    "location": "File > Export",
    "warning": "", # used for warning icon and text in addons panel
    "category": "Export",
}

def write_int32(int):
    tmp = f"{struct.unpack('>I', struct.pack('<I', int))[0]:08X}"
    return tmp

def write_float(float):
    tmp = f"{struct.unpack('>I', struct.pack('<f', float))[0]:08X}"
    return tmp
    
def batch_write_int32(list):
    tmp = ""
    for x in list:
        tmp += f"{struct.unpack('>I', struct.pack('<I', x))[0]:08X} "
    return tmp

def batch_write_float(list):
    tmp = ""
    for x in list:
        tmp += f"{struct.unpack('>I', struct.pack('<f', x))[0]:08X} "
    return tmp

def get_sector_size(array):
    tmp = len(bytes.fromhex(f"{intb(1)} {intb(1)} {intb(1)} {array}"))
    tmp = intb(tmp)
    return tmp

def pad_bytes(length):
    l = [0] * (length//4)
    pad = ""
    for v in l:
        pad += (f"{write_int32(v)}")
    return pad

def get_ahi():
    object = bpy.context.active_object
    if object.type == 'ARMATURE':
        finalbytes = ""
        bone_sector = ""
        bones = object.data.bones
        bone_count = len(object.data.bones)
        root_bones = object.get('root_bones')
        #if root_bones == None:
        #    return
        
        root_data = f"{write_int32(0x00000000)} {write_int32(len(root_bones))} {write_int32((len(root_bones) * 4) + 0xC)}"
        for x in range(len(root_bones)):
            root_data += f"{write_int32(root_bones[x])} "

        full_size = (bone_count*0x10C) + len(bytes.fromhex(root_data)) + 0xC
        header_data = f"{write_int32(0xC0000000)} {write_int32(bone_count+1)} {write_int32(full_size)} "
        
        for bone in bones:
            #bone = object.data.bones[str(x)]
            bone_parent = bone.parent
            bone_child = bone.get('bone_child')
            bone_unknown1 = bone.get('bone_unknown1')
            trans_inherit = bone.get('trans_inherit_mesh')
            bone_type = bone.get('bone_type')
            bone_scale = bone.get('bone_scale')
        
            loc, rot, sca = bone.matrix_local.decompose()
            rot = rot.to_euler('XYZ')
            
            print(loc)
            
            if bone_parent == None:
                bone_parent = f"FFFFFFFF"
            else:
                bone_parent = f"{write_int32(int(bone_parent.name))}"
                parent_loc, parent_rot, parent_sca = bone.parent.matrix_local.decompose()
                parent_rot = parent_rot.to_euler('XYZ')
                
                loc -= parent_loc
                rot == (rot[0] -  parent_rot[0], rot[1] - parent_rot[1], rot[2] - parent_rot[2] )
                sca -= parent_sca
                                
            if bone_child == -1:
                bone_child = f"FFFFFFFF"
            else:
                bone_child = f"{write_int32(bone_child)}"
            if bone_unknown1 == -1:
                bone_unknown1 = f"FFFFFFFF"
            else:
                bone_unknown1 = f"{write_int32(bone_unknown1)}"
            if trans_inherit == -1:
                trans_inherit = f"FFFFFFFF"
            else:
                trans_inherit = f"{write_int32(trans_inherit)}"
            
            if bone_type == 1:
                bone_type = f"01000040"
            elif bone_type == 2:
                bone_type = f"02000040"
            
            position = f"{write_float(loc[0])} {write_float(loc[1])} {write_float(loc[2])} {write_float(1.0)}"
            rotation = f"{write_float(rot[0])} {write_float(rot[1])} {write_float(rot[2])} {write_float(1.0)}"
            scale = f"{write_float(bone_scale[0])} {write_float(bone_scale[1])} {write_float(bone_scale[2])} {write_float(bone_scale[3])}"
            
            boneID = f"{write_int32(int(bone.name))}"
            
            data = f"{bone_type} {write_int32(1)} {write_int32(0x10C)} "
            data += f"{boneID} {bone_parent} {bone_child} {bone_unknown1} "
            data += f"{scale} {rotation} {position} {trans_inherit} "
            data += f"{pad_bytes(0xBC)} "
            bone_sector += data
            
            finalbytes = f"{header_data} {root_data} {bone_sector}"
            
        return bytes.fromhex(finalbytes)

def write_some_data(context, filepath):
    print("running write_some_data...")
    ahi = get_ahi()
    f = open(filepath, 'wb')
    f.write(ahi)
    f.close()

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class Export_AHI(Operator, ExportHelper):
    """Export selected armature object as Artistoon Armature data."""
    bl_idname = "export_scene.ahi"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Artistoon Armature"

    # ExportHelper mixin class uses this
    filename_ext = ".ahi"

    filter_glob: StringProperty(
        default="*.ahi",
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
        return write_some_data(context, self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(Export_AHI.bl_idname, text="Artistoon Armature (.ahi)")


# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
def register():
    bpy.utils.register_class(Export_AHI)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(Export_AHI)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_scene.ahi('INVOKE_DEFAULT')
