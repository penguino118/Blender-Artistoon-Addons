import bpy

class AMOMaterialPanel(bpy.types.Panel):
    bl_label = "Artistoon Material Settings"
    bl_idname = "ARTISTOON_PT_Material"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        material = context.object.active_material
        return material != None

    def draw(self, context):
        try:
            layout = self.layout.box()
            row = layout.row()
            row.prop(context.material, "AMO_MaterialType")
            row.prop(context.material, "AMO_TextureIndex")
            row = layout.row()
            row.prop(context.material, "AMO_TextureWidth")
            row.prop(context.material, "AMO_TextureHeight")
            row = layout.row()
            row.prop(context.material, "AMO_ColorUnk1")
            row = layout.row()
            row.prop(context.material, "AMO_ColorUnk2")
            row = layout.row()
            row.prop(context.material, "AMO_ColorUnk3")
            row = layout.row()
            row.prop(context.material, "AMO_Unknown4")
            row.prop(context.material, "AMO_Unknown5")
        except:
            pass
        
def register():
    bpy.utils.register_class(AMOMaterialPanel)
    bpy.types.Material.AMO_MaterialType  = bpy.props.IntProperty(name = "Material Type", min=0x0, max=0xFFFFFFF, default=0x00)
    bpy.types.Material.AMO_TextureIndex  = bpy.props.IntProperty(name = "Texture Index", min=0x0, max=0xFFFFFFF, default=0x00)
    bpy.types.Material.AMO_TextureWidth  = bpy.props.IntProperty(name = "Width", min=0x0, max=1024, step=16, default=16)
    bpy.types.Material.AMO_TextureHeight = bpy.props.IntProperty(name = "Height", min=0x0, max=1024, step=16, default=16)
    bpy.types.Material.AMO_ColorUnk1     = bpy.props.FloatVectorProperty(name = "Unknown 1", subtype = "COLOR", size = 4, min = 0.0, max = 1.0, default = (0.25,0.25,0.25, 0.5))
    bpy.types.Material.AMO_ColorUnk2     = bpy.props.FloatVectorProperty(name = "Unknown 2", subtype = "COLOR", size = 4, min = 0.0, max = 1.0, default = (0.5, 0.5, 0.5, 0.75))
    bpy.types.Material.AMO_ColorUnk3     = bpy.props.FloatVectorProperty(name = "Unknown 3", subtype = "COLOR", size = 4, min = 0.0, max = 1.0, default = (1.0, 1.0, 1.0, 1.0))
    bpy.types.Material.AMO_Unknown4      = bpy.props.FloatProperty(name = "Unknown 4", default = 50.0)
    bpy.types.Material.AMO_Unknown5      = bpy.props.IntProperty(name = "Unknown 5", min=0x0, max=0xFFFFFFF, default=0x01)


def unregister():
    bpy.utils.unregister_class(AMOMaterialPanel)
    del bpy.types.Material.AMO_MaterialType
    del bpy.types.Material.AMO_TextureIndex
    del bpy.types.Material.AMO_TextureWidth
    del bpy.types.Material.AMO_TextureHeight
    del bpy.types.Material.AMO_ColorUnk1
    del bpy.types.Material.AMO_ColorUnk2
    del bpy.types.Material.AMO_ColorUnk3
    del bpy.types.Material.AMO_Unknown4
    del bpy.types.Material.AMO_Unknown5


if __name__ == "__main__":
    register()