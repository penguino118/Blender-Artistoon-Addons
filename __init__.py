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
    "description": "Importer and exporter for various formats used in the Artistoon engine found in GioGio's Bizarre Adventure.",
    "author": "Penguino",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "File > Import-Export",
    "warning": "", # used for warning icon and text in addons panel
    "category": "Import-Export",
}


### classes ###
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator

# EXPORT #

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
    
    user_scale: FloatProperty(
        name="Scale",
        description="Scale by which the objects will be transformed on export",
        default=10.0,
        min=0.001,
        max=1000.0,
    )
    
    z_up: BoolProperty(
        name="Rotate Up Axis",
        description="Rotates the object so it faces up in the Z axis",
        default=True,
    )

    def execute(self, context):
        from .file_handling.artistoon_export import AHI_exporter
        return AHI_exporter.write(context, self.filepath, self.z_up, self.user_scale)

class Export_AMO(Operator, ExportHelper):
    """Export selected collection as Artistoon Model data."""
    bl_idname = "export_scene.amo"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Artistoon Model"

    # ExportHelper mixin class uses this
    filename_ext = ".amo"

    filter_glob: StringProperty(
        default="*.amo",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
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
        from .file_handling.artistoon_export import AMO_exporter
        return AMO_exporter.write(context, self.filepath, self.uv_split, self.face_type, self.normal_type, self.user_scale, self.z_up)


# IMPORT #

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

    def execute(self, context):
        from .file_handling.artistoon_import import AAN_importer
        return AAN_importer.read(context, self.filepath)

class Import_AHI(Operator, ImportHelper):
    """Import Artistoon Armature data into a new collection."""
    bl_idname = "import_scene.ahi"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Artistoon Armature"

    # ImportHelper mixin class uses this
    filename_ext = ".ahi/.bin"
    
    filter_glob: StringProperty(
        default="*.ahi;*.bin",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    
    user_scale: FloatProperty(
        name="Scale",
        description="Scale by which the object will be transformed",
        default=0.1,
        min=0.001,
        max=1000.0,
    )
    
    z_up: BoolProperty(
        name="Rotate Up Axis",
        description="Rotates the object so it faces up in the Z axis",
        default=True,
    )

    def execute(self, context):
        from .file_handling.artistoon_import import AHI_importer
        return AHI_importer.read(context, self.filepath, self.user_scale, self.z_up)

class Import_AMO(Operator, ImportHelper):
    """Import Artistoon Model data as a new collection."""
    bl_idname = "import_scene.amo"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Artistoon Model"

    # ImportHelper mixin class uses this
    filename_ext = ".amo/.bin"

    filter_glob: StringProperty(
        default="*.amo;*.bin",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    user_scale: FloatProperty(
        name="Scale",
        description="Scale by which the objects will be transformed",
        default=0.1,
        min=0.001,
        max=1000.0,
    )
    
    z_up: BoolProperty(
        name="Rotate Up Axis",
        description="Rotates the objects so the meshes face up in the Z axis",
        default=True,
    )
    
    def execute(self, context):
        from .file_handling.artistoon_import import AMO_importer
        return AMO_importer.read(context, self.filepath, self.z_up, self.user_scale) # self.use_setting

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
        return archive_io.load_from_pzz(context, self.filepath, self.use_z_up, self.user_scale)

### ###


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(Export_AHI.bl_idname, text="Artistoon Armature (.ahi)")
    self.layout.operator(Export_AMO.bl_idname, text="Artistoon Model (.amo)")

def menu_func_import(self, context):
    self.layout.operator(Import_AAN.bl_idname, text="Artistoon Animation (.aan)")
    self.layout.operator(Import_AHI.bl_idname, text="Artistoon Armature (.ahi)")
    self.layout.operator(Import_AMO.bl_idname, text="Artistoon Model (.amo)")

    self.layout.operator(Import_PZZ.bl_idname, text="GioGio PZZ (.pzz)")

# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).

classes = [
    Export_AHI,
    Export_AMO,
    Import_AAN,
    Import_AHI,
    Import_AMO
    ]

from .blender import AHI_bone_attribute_panel
from .blender import AMO_mesh_attribute_panel
from .blender import AMO_material_panel
from .blender import PZZ_entry_panel

def register():
    for art_class in classes:
        bpy.utils.register_class(art_class)
    bpy.utils.register_class(Import_PZZ)
    AHI_bone_attribute_panel.register()
    AMO_mesh_attribute_panel.register()
    AMO_material_panel.register()
    PZZ_entry_panel.register()
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    for art_class in classes:
        bpy.utils.unregister_class(art_class)
    bpy.utils.unregister_class(Import_PZZ)
    AMO_mesh_attribute_panel.unregister()
    AMO_material_panel.unregister()
    PZZ_entry_panel.unregister()
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

