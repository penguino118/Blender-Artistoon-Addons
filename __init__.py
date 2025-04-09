import importlib
import sys

current_package_prefix = f"{__name__}." # so reload works properly
for name, module in sys.modules.copy().items():
    if name.startswith(current_package_prefix):
        try: 
            importlib.reload(module)
            print(f"{current_package_prefix}: Reloading {name}")
        except:
            print(f"{current_package_prefix}: {name} failed.")

# pylint: disable=fixme, import-error
import bpy

bl_info = {
    "name": "Blender Artistoon Model Addons",
    "description": "Importer and exporter for various Artistoon engine formats, found in GioGio's Bizarre Adventure.",
    "author": "Penguino",
    "version": (2, 0),
    "blender": (4, 4, 0),
    "location": "File > Import-Export",
    "warning": "", # used for warning icon and text in addons panel
    "category": "Import-Export",
}


### classes ###
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator


class Export_PZZ(Operator, ImportHelper):
    """Export active collection into an existing PZZ archive."""
    bl_idname = "export_scene.pzz"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Collection into GioGio PZZ (.pzz)"

    # ImportHelper mixin class uses this
    filename_ext = ".pzz"

    filter_glob: StringProperty(
        default="*.pzz",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    user_scale: FloatProperty(
        name="Import Scale",
        description="Scale by which the objects will be transformed",
        default=0.1,
        min=0.001,
        max=1000.0,
    )
    
    user_scale: FloatProperty(
        name="Scale",
        description="Scale by which the objects will be transformed on export",
        default=10.0,
        min=0.001,
        max=1000.0,
    )
    
    face_type: EnumProperty(
        name="Index Mode",
        description="How the exported model will store face indices",
        items=(
            ('TRI_STRIP', "Triangle Strip", "Compatible triangles are connected together to save memory"),
            ('TRI_LIST', "Triangle List", "Each triangle is stored separately, less memory efficient"),
        ),
        default='TRI_STRIP',
    )
    
    normal_type: EnumProperty(
        name="Normal Export",
        description="What type of normal data will be exported",
        items=(
            ('LOOP_NORMALS', "Loop Normals", "Use normals stored in face loops."),
            ('VERT_NORMALS', "Vertex Normals", "Use vertex normals, doesn't take into account sharp faces, sharp edges, or custom normal data"),
        ),
        default='LOOP_NORMALS',
    )
    
    normal_split: BoolProperty(
        name="Split Faces by Normals",
        description="Automatically splits face corners that make vertices have multiple UVs to safely store them per vertex",
        default=True,
    )
    
    uv_split: BoolProperty(
        name="Split Faces by UVs",
        description="Automatically splits face corners that make vertices have multiple UVs to safely store them per vertex",
        default=True,
    )
    
    z_up: BoolProperty(
        name="Rotate Up Axis",
        description="Rotates the object's orientation from Blender's Z up",
        default=True,
    )
    
    def execute(self, context):
        from .file_handling import archive_io
        return archive_io.export_to_pzz(self, self.filepath, self.user_scale, self.face_type, self.normal_type, self.uv_split, self.z_up)


class Import_PZZ(Operator, ImportHelper):
    """Import models and animations from PZZ archive."""
    bl_idname = "import_scene.pzz"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "GioGio PZZ (.pzz)"

    # ImportHelper mixin class uses this
    filename_ext = ".pzz"

    filter_glob: StringProperty(
        default="*.pzz",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    user_scale: FloatProperty(
        name="Import Scale",
        description="Scale by which the objects will be transformed",
        default=0.1,
        min=0.001,
        max=1000.0,
    )
    
    use_z_up: BoolProperty(
        name="Rotate Up Axis",
        description="Rotates the objects so the objects face up in the Z axis",
        default=True,
    )
    
    def execute(self, context):
        from .file_handling import archive_io
        return archive_io.load_from_pzz(self, self.filepath, self.use_z_up, self.user_scale)


### ###
# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(Export_PZZ.bl_idname, text="GioGio PZZ (.pzz)")

def menu_func_import(self, context):
    self.layout.operator(Import_PZZ.bl_idname, text="GioGio PZZ (.pzz)")


# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
from .blender import AHI_bone_attribute_panel
from .blender import AMO_mesh_attribute_panel
from .blender import AMO_material_panel
from .blender import PZZ_entry_panel

def register():
    bpy.utils.register_class(Import_PZZ)
    bpy.utils.register_class(Export_PZZ)
    AHI_bone_attribute_panel.register()
    AMO_mesh_attribute_panel.register()
    AMO_material_panel.register()
    PZZ_entry_panel.register()
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(Import_PZZ)
    bpy.utils.unregister_class(Export_PZZ)
    AHI_bone_attribute_panel.unregister()
    AMO_mesh_attribute_panel.unregister()
    AMO_material_panel.unregister()
    PZZ_entry_panel.unregister()
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

