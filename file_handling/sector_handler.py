from .binary_rw import int32_write, int32_read

def get_sector_info(buffer, offset):
    head = int32_read(buffer, offset)
    count = int32_read(buffer, offset+4)
    size = int32_read(buffer, offset+8)

    return {
        "header" : head,
        "data_count" : count,
        "data_size" : size
    }


def insert_header(byte_array, sector_key, data_count):
    sector_size = len(byte_array) + 0xC
    byte_array[0:0] = int32_write(sector_key)
    byte_array[4:4] = int32_write(data_count)
    byte_array[8:8] = int32_write(sector_size)


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
    "Magic"          : 0xC0000000,     
    "HierarchyRoots" : 0x00000000, # Roots of the bone hierarchy
    "BoneNode"       : 0x40000000  # is OR'd by some 'type' indicator, type 1 is used on characters and 2 on stages
    }

# Model
AMO_sector_dict = { 
    "Magic"             : 0x00000001,
    "Unknown0002"       : 0x00020000, # Never fetched by GetSubDataAMO
    "ModelHeader"       : 0x00000002, #  function: GetModelNum, plAMOGetModelHead
    "MeshDataContainer" : 0x00000004, 
    "TriStripContainer" : 0x00000005, #  function: GetIndexListAMOModelMesh, GetIndexListDescAMOModelMesh, GetPrimitiveNumAMOModelMesh, GetPrimVertexNumAMOModelMesh, GetPrimCullTypeAMOModelMesh
    "TriStrips"         : 0x00030000, 
    "TriStripsComplex"  : 0x00040000, # For tristrips with vertices that have multiple bones influencing them
    "MeshMaterialList"  : 0x00050000, #  function: plAMOGetMaterialListNum, plAMOGetMaterialList // materials of the mesh, not all 
    "MaterialIndices"   : 0x00060000, #  function: GetMaterialIndexAMOModelMesh // materials per triangle strip
    "VertexCoordinates" : 0x00070000, #  function: GetVertexNumAMOModelMesh, GetVertexAMOModelMesh
    "VertexNormals"     : 0x00080000, #  function: GetNormalAMOModelMesh
    "VertexUVs"         : 0x000A0000, #  function: GetStAMOModelMesh
    "VertexColors"      : 0x000B0000, #  function: GetVertexColorAMOModelMesh
    "VertexWeights"     : 0x000C0000, #  function: GetWeightNumAMOModelMesh, GetWeightAMOModelMesh
    "Unknown000E"       : 0x000E0000, # Never fetched by GetSubDataAMO, only present in st021.pzz
    "Attributes"        : 0x000F0000, #  function: PlAMOGetModelAttributes
    "BoundingBox"       : 0x00110000, #  function: plAMOGetBoundingModel // bounding box, used for occlusion culling in stage models
    "MaterialList"      : 0x00000009, #  function: plAMOGetMaterialNum, plAMOGetMaterialHead
    "TextureList"       : 0x0000000A  #  function: plAMOGetTextureHead
    }

