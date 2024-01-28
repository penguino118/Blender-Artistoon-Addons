from .binary_rw import int32_write


def get_sector_size(array):
    tmpb = 0x4
    for fun in array:
        print(fun.hex())
        ppp = fun.hex()
        tmpb += int(len(ppp)/2)
    tmpb = int32_write(tmpb)
    return tmpb

# Animation
AAN_sector_dict = {
    0x80000001  : "AnimationBlock01",
    0x80000002  : "AnimationBlock02",
    0x80000000  : "ProbablyImportant",
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

# Armature
AHI_sector_dict = {
    0xC0000000  : "AHI_magic",       #start of the file #count is global sector count
    0x00000000  : "AHI_tree_root",   #tree root model number (??)
    0x40000001  : "AHI_bone_type_1", #bone type 1
    0x40000002  : "AHI_bone_type_2", #bone type 1
    }

# Model
AMO_sector_dict = { 
    0x00000001 : "AMO_magic",
    0x00020000 : "AMO_unknown",             #something about RAM?
    0x00000002 : "AMO_model_container",     #game func: GetModelNum
    0x00000004 : "AMO_mesh_container",
    0x00000005 : "AMO_tristrip_container",  #GetIndexListAMOModelMesh
    0x00030000 : "AMO_tristrip_03_data",
    0x00040000 : "AMO_tristrip_04_data",    #triangles with multiple bone deformations
    0x00050000 : "AMO_material_list",       #per mesh material
    0x00060000 : "AMO_material_per_strip",
    0x00070000 : "AMO_vertex_coordinates",  #GetVertexAMOModelMesh
    0x00080000 : "AMO_vertex_normals",      #GetNormalAMOModelMesh
    0x000A0000 : "AMO_vertex_UVs",
    0x000B0000 : "AMO_vertex_colors",       #GetVertexColorAMOModelMesh
    0x000C0000 : "AMO_vertex_groups",       #GetWeightAMOModelMesh
    0x000E0000 : "AMO_unused_unknown",      #Never called by GetSubDataAMO, only present in st021
    0x000F0000 : "AMO_mesh_attributes",     #PlAMOGetModelAttributes
    0x00110000 : "AMO_hitbox_identifier",   #bounding model fetch, used for stages
    0x00000009 : "AMO_material_properties", #global
    0x0000000A : "AMO_texture_properties"
    }

