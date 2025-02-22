import bpy


class AHIBonePanel(bpy.types.Panel):
    bl_label = "Artistoon Bone Attributes"
    bl_idname = "ARTISTOON_PT_Bone"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "bone"
    
    @classmethod
    def poll(cls, context):
        bone = context.edit_bone
        return bone and bone.select == True
    
    def draw(self, context):
        layout = self.layout
        layout_box = layout.box()
        row = layout_box.row(align=True, heading="Attached Mesh")
        row.prop(context.edit_bone, "AHI_MeshPointer")
        


def poll_meshes(self, object):
    return object.type == 'MESH' and object.parent.type == 'ARMATURE'


def register():
    bpy.utils.register_class(AHIBonePanel)
    
    bpy.types.EditBone.AHI_MeshPointer = bpy.props.PointerProperty(
        name="",
        type=bpy.types.Object,
        poll=poll_meshes)


def unregister():
    bpy.utils.unregister_class(AHIBonePanel)
    del bpy.types.Mesh.AHI_MeshPointer


if __name__ == "__main__":
    register()