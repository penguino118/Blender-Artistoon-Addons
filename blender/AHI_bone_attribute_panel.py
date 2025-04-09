import bpy


class AHIBonePanel(bpy.types.Panel):
    bl_label = "Artistoon Bone Attributes"
    bl_idname = "ARTISTOON_PT_Bone"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "bone"
    
    @classmethod
    def poll(cls, context):
        bone = context.bone
        if bone == None: return False
        else: return bone and bone.select or bone.select_head or bone.select_tail
    
    def draw(self, context):
        layout = self.layout
        row = layout.column()
        row.label(text="Shadow Volume Size")
        row = layout.row()
        row.prop(context.bone, "AHI_ShadowVolumeSize", text='')
        

def register():
    bpy.utils.register_class(AHIBonePanel)
    bpy.types.Bone.AHI_ShadowVolumeSize = bpy.props.FloatVectorProperty(name = "Shadow Volume Size", subtype = "XYZ_LENGTH", size = 4, default = (1.0,1.0,1.0,1.0))


def unregister():
    bpy.utils.unregister_class(AHIBonePanel)
    del bpy.types.Bone.AHI_ShadowVolumeSize


if __name__ == "__main__":
    register()