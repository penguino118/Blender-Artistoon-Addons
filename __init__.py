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
from bpy.props import StringProperty, BoolProperty, EnumProperty
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

    def execute(self, context):
        from .file_handling.artistoon_export import AHI_exporter
        return AHI_exporter.write(context, self.filepath)

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
    
    face_type: EnumProperty(
        name="Index Mode",
        description="How the exported model will store face indices",
        items=(
            ('TRI_STRIP', "Triangle Strip", "Compatible triangles are connected together to save memory"),
            ('TRI_LIST', "Triangle List", "Each triangle is stored separately, less memory efficient"),
        ),
        default='TRI_STRIP',
    )
    
    uv_split: BoolProperty(
        name="Split Faces by UVs",
        description="Automatically splits face corners that make vertices have multiple UVs to safely store them per vertex",
        default=True,
    )
    
    def execute(self, context):
        from .file_handling.artistoon_export import AMO_exporter
        return AMO_exporter.write(context, self.filepath, self.uv_split, self.face_type)


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

    z_up: BoolProperty(
        name="Rotate Z to up",
        description="Rotates the object so it faces up in the Z axis.",
        default=True,
    )

    def execute(self, context):
        from .file_handling.artistoon_import import AHI_importer
        return AHI_importer.read(context, self.filepath, self.z_up)

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
    z_up: BoolProperty(
        name="Rotate Z to up",
        description="Rotates the objects so the meshes face up in the Z axis.",
        default=True,
    )
    
    def execute(self, context):
        from .file_handling.artistoon_import import AMO_importer
        return AMO_importer.read(context, self.filepath, self.z_up) # self.use_setting

### ###


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(Export_AHI.bl_idname, text="Artistoon Armature (.ahi)")
    self.layout.operator(Export_AMO.bl_idname, text="Artistoon Model (.amo)")

def menu_func_import(self, context):
    self.layout.operator(Import_AAN.bl_idname, text="Artistoon Animation (.aan)")
    self.layout.operator(Import_AHI.bl_idname, text="Artistoon Armature (.ahi)")
    self.layout.operator(Import_AMO.bl_idname, text="Artistoon Model (.amo)")

# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).

classes = [
    Export_AHI,
    Export_AMO,
    Import_AAN,
    Import_AHI,
    Import_AMO
    ]

def register():
    for art_class in classes:
        bpy.utils.register_class(art_class)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    for art_class in classes:
        bpy.utils.unregister_class(art_class)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

