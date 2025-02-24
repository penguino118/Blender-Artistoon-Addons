import bpy

class AMOMaterialPanel(bpy.types.Panel):
    bl_label = "PZZ Entry Information"
    bl_idname = "PZZ_PT_EntryData"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    
    @classmethod
    def poll(cls, context):
        object = context.object
        return object and object.type == 'ARMATURE' or object.type == 'EMPTY' 
    
    def draw(self, context):
        layout = self.layout
        layout_box = layout.box()
        row = layout_box.row()
        row.prop(context.object, "PZZ_Index")
        row.prop(context.object, "PZZ_Compressed")


def register():
    bpy.utils.register_class(AMOMaterialPanel)
    bpy.types.Object.PZZ_Compressed = bpy.props.BoolProperty(name='Compressed')
    bpy.types.Object.PZZ_Index      = bpy.props.IntProperty(name = "PZZ Index", min=0x0, max=512, default=0)


def unregister():
    bpy.utils.unregister_class(AMOMaterialPanel)
    del bpy.types.Object.PZZ_Compressed
    del bpy.types.Object.PZZ_Index


if __name__ == "__main__":
    register()