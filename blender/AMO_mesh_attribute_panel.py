import bpy

class AMOMaterialPanel(bpy.types.Panel):
    bl_label = "Artistoon Mesh Attributes"
    bl_idname = "ARTISTOON_PT_Attributes"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    def draw(self, context):
        layout = self.layout
        layout_box = layout.box()
        
        
        
        row = layout_box.row()
        row.prop(context.mesh, "AMO_HasBounding")
        row = layout_box.row()
        if context.object.data.AMO_HasBounding:
            row.prop(context.mesh, "AMO_Bounding")
        else:
            row = layout_box.row()
            row.prop(context.mesh, "AMO_RenderDistance")
            row = layout_box.row()
            row.prop(context.mesh, "AMO_Culling")
            row = layout_box.row()
            row.prop(context.mesh, "AMO_Scissor")
            row.prop(context.mesh, "AMO_Light")
            row = layout_box.row()
            row.prop(context.mesh, "AMO_UVScroll")
            row.prop(context.mesh, "AMO_FadeColor")
            row = layout_box.row()
            row.prop(context.mesh, "AMO_Special")
            row.prop(context.mesh, "AMO_Unknown_0x10")
            row = layout_box.row()
            row.prop(context.mesh, "AMO_Unknown_0x14")
            row.prop(context.mesh, "AMO_Unknown_0x24")
            row.prop(context.mesh, "AMO_Unknown_0x2C")
            row.prop(context.mesh, "AMO_Unknown_0x38")
            row.prop(context.mesh, "AMO_Unknown_0x3C")
            row = layout_box.row()
            row.prop(context.mesh, "AMO_Unknown_0x40")
            row.prop(context.mesh, "AMO_Unknown_0x44")
            row.prop(context.mesh, "AMO_Unknown_0x48")
            row.prop(context.mesh, "AMO_Unknown_0x4C")
            row.prop(context.mesh, "AMO_Unknown_0x50")
        
def register():
    bpy.utils.register_class(AMOMaterialPanel)

    '''
    0x0C, #max render distance (unused?)
    0x10, #aa_material (dunno)
    0x14, 
    0x18, #aa_cull (unused?)
    0x1C, #aa_scissor (bool for oclussion culling)
    0x20, #aa_light (set to 2 in transparent meshes)
    0x24, 
    0x28, #aa_uvscroll (...for main menu clouds?)
    0x2C, 
    0x30, #aa_fadecolor (dunno) 
    0x34, #aa_special (dunno) 
    0x38, 
    0x3C, 
    0x40, 
    0x44, 
    0x48,
    0x4C,
    0x50'''
    
    bpy.types.Mesh.AMO_RenderDistance = bpy.props.IntProperty( name = "Maximum Render Distance", min=0x0, max=0x7FFFFFFF, default=65536)
    bpy.types.Mesh.AMO_Unknown_0x10   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x01) # aa_material? in struct 
    bpy.types.Mesh.AMO_Unknown_0x14   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Culling        = bpy.props.IntProperty(name = "Culling Flag", min=0x0, max=0x7FFFFFFF, default=0x1)
    bpy.types.Mesh.AMO_Scissor        = bpy.props.IntProperty(name = "Scissor Flag", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Light          = bpy.props.IntProperty(name = "Light Flag", min=0x0, max=0x7FFFFFFF, default=0x02)
    bpy.types.Mesh.AMO_Unknown_0x24   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_UVScroll       = bpy.props.IntProperty(name = "UV Scroll", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Unknown_0x2C   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_FadeColor      = bpy.props.IntProperty(name = "Fade Color", min=0x0, max=0x7FFFFFFF, default=0x01)
    bpy.types.Mesh.AMO_Special        = bpy.props.IntProperty(name = "Special Flag", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Unknown_0x38   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Unknown_0x3C   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Unknown_0x40   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Unknown_0x44   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Unknown_0x48   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Unknown_0x4C   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_Unknown_0x50   = bpy.props.IntProperty(name = "Unknown", min=0x0, max=0x7FFFFFFF, default=0x00)
    bpy.types.Mesh.AMO_HasBounding    = bpy.props.BoolProperty(name='Is Stage Mesh')
    bpy.types.Mesh.AMO_Bounding       = bpy.props.FloatVectorProperty(name = "Bounding Box Size", subtype = "XYZ_LENGTH", size = 4, default = (0.0,0.0,0.0,0.0))


def unregister():
    bpy.utils.unregister_class(AMOMaterialPanel)
    del bpy.types.Mesh.AMO_RenderDistance
    del bpy.types.Mesh.AMO_Unknown_0x10
    del bpy.types.Mesh.AMO_Unknown_0x14
    del bpy.types.Mesh.AMO_Culling
    del bpy.types.Mesh.AMO_Scissor
    del bpy.types.Mesh.AMO_Light
    del bpy.types.Mesh.AMO_Unknown_0x24
    del bpy.types.Mesh.AMO_UVScroll
    del bpy.types.Mesh.AMO_Unknown_0x2C
    del bpy.types.Mesh.AMO_FadeColor
    del bpy.types.Mesh.AMO_Special
    del bpy.types.Mesh.AMO_Unknown_0x38
    del bpy.types.Mesh.AMO_Unknown_0x3C
    del bpy.types.Mesh.AMO_Unknown_0x40
    del bpy.types.Mesh.AMO_Unknown_0x44
    del bpy.types.Mesh.AMO_Unknown_0x48
    del bpy.types.Mesh.AMO_Unknown_0x4C
    del bpy.types.Mesh.AMO_Unknown_0x50
    del bpy.types.Mesh.AMO_HasBounding
    del bpy.types.Mesh.AMO_Bounding



if __name__ == "__main__":
    register()