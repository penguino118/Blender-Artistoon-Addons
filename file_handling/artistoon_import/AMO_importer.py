import bpy
import os
import bmesh
import math
import mathutils
from ..sector_handler import get_sector_info, AMO_sector_dict as sector_types
from ..binary_rw import int16_read, int32_read, float_read

z_up_rotation = mathutils.Euler((math.radians(90.0), 0.0, math.radians(180.0)), 'XYZ')


def create_material(material_name, material_property):
    material = bpy.data.materials.new(material_name)
    
    material.AMO_MaterialType  = material_property["AMO_MaterialType"]
    material.AMO_TextureIndex  = material_property["AMO_TextureIndex"]
    material.AMO_TextureWidth  = material_property["AMO_TextureWidth"]
    material.AMO_TextureHeight = material_property["AMO_TextureHeight"]
    material.AMO_ColorUnk1     = material_property["AMO_ColorUnk1"]
    material.AMO_ColorUnk2     = material_property["AMO_ColorUnk2"]
    material.AMO_ColorUnk3     = material_property["AMO_ColorUnk3"]
    material.AMO_Unknown4      = material_property["AMO_Unknown4"]
    material.AMO_Unknown5      = material_property["AMO_Unknown5"]
    
    return material


def build_materials(filename, buffer, offset, material_offset_start):
    print("Building materials...")
    
    texture_property_list = []
    material_property_list = []
    offset += material_offset_start
    
    # read through material entries
    material_properties = get_sector_info(buffer, offset)
    if material_properties["header"] == sector_types["MaterialList"]:
        offset += 0xC
        for x in range(material_properties["data_count"]):
            material_type = int32_read(buffer, offset)
            # i assume these are color values for shadow, diffuse, and specular
            # they're not actually use for rendering though... so who knows what it's actually for
            color_unk1 = float_read(buffer, offset+0x0C), float_read(buffer, offset+0x10), float_read(buffer, offset+0x14), float_read(buffer, offset+0x18)
            color_unk2 = float_read(buffer, offset+0x1C), float_read(buffer, offset+0x20), float_read(buffer, offset+0x24), float_read(buffer, offset+0x28)
            color_unk3 = float_read(buffer, offset+0x2C), float_read(buffer, offset+0x30), float_read(buffer, offset+0x34), float_read(buffer, offset+0x38)
            unknown_4 = float_read(buffer, offset+0x3C)
            unknown_5 = int32_read(buffer, offset+0x40)
            texture_list_index = int32_read(buffer, offset+0x10C)

            material_property_list.append({
            "AMO_MaterialType"  : material_type,
            "AMO_TextureIndex"  : texture_list_index, # will be update das we pass through the texture list
            "AMO_TextureWidth"  : -1, # will be updated as we pass through the texture list
            "AMO_TextureHeight" : -1, # will be updated as we pass through the texture list
            "AMO_ColorUnk1"     : color_unk1,
            "AMO_ColorUnk2"     : color_unk2,
            "AMO_ColorUnk3"     : color_unk3,
            "AMO_Unknown4"      : unknown_4,
            "AMO_Unknown5"      : unknown_5
            })
            
            material_entry_size = int32_read(buffer, offset+0x8)
            offset += material_entry_size
    
    # read through texture entries
    texture_properties = get_sector_info(buffer, offset)
    if texture_properties["header"] == sector_types["TextureList"]:
        offset += 0xC
        for x in range(texture_properties["data_count"]):
            texture_index  = int32_read(buffer, offset+0xC)
            texture_width  = int32_read(buffer, offset+0x10)
            texture_height = int32_read(buffer, offset+0x14)

            texture_property_list.append({
            "TextureIndex" : texture_index,
            "TextureWidth" : texture_width,
            "TextureHeight" : texture_height
            })

            texture_entry_size = int32_read(buffer, offset+0x8)
            offset += texture_entry_size
    
    # update material properties with texture list properties (index, width, height)
    for material_property in material_property_list:
        
        texture_list_index = material_property["AMO_TextureIndex"]
        texture_property = texture_property_list[texture_list_index]

        material_property["AMO_TextureIndex"] = texture_property["TextureIndex"]
        material_property["AMO_TextureWidth"] = texture_property["TextureWidth"]
        material_property["AMO_TextureHeight"] = texture_property["TextureHeight"]

    # create the materials
    all_materials_list = []
    for index in range(len(material_property_list)):
        material_property = material_property_list[index]
        all_materials_list.append(create_material(f"{filename[:-4]}_mat{index}", material_property))
    return all_materials_list


def get_indices(buffer, offset, strip_count, list, strip_length_list):
    offset += 0xC
    for x in range(strip_count):
        count = int16_read(buffer, offset)
        strip_length_list.append(count-2)
        index_list = []
        #cull_mode = int16_read(buffer, offset) # not actually used in rendering?
        offset += 0x4
        for y in range(count):
            vert_index = int32_read(buffer, offset)
            index_list.append(vert_index)  
            offset += 0x4
        # convert tri strip to tri list
        for y in range(len(index_list)-2):
            if (y % 2) == 0:
                list.append([index_list[y], index_list[y+1], index_list[y+2]])
            else:
                list.append([index_list[y], index_list[y+2], index_list[y+1]])


def get_vert_coords(buffer, offset, sector_size, vertex_count, list, scale, use_z_up):
    for x in range(vertex_count):
        vertpos = mathutils.Vector((float_read(buffer, offset)*scale, float_read(buffer, offset+0x4)*scale, float_read(buffer, offset+0x8)*scale))
        if use_z_up: vertpos.rotate(z_up_rotation)
        list.append(vertpos)
        offset += 0xC
        if offset >= sector_size:
            return


def get_vert_normals(buffer, offset, sector_size, vertex_count, list, use_z_up):
    for x in range(vertex_count):
        normal = mathutils.Vector((float_read(buffer, offset), float_read(buffer, offset+0x4), float_read(buffer, offset+0x8)))
        if use_z_up: normal.rotate(z_up_rotation)
        list.append(normal)
        offset += 0xC
        if offset >= sector_size:
            return


def get_vert_uvs(buffer, offset, sector_size, vertex_count, list):
    for x in range(vertex_count):
        uv = float_read(buffer, offset), 1.0-float_read(buffer, offset+0x4)
        list.append(uv)
        offset += 0x8
        if offset >= sector_size:
            return
      
      
def get_vert_colors(buffer, offset, sector_size, vertex_count, list):
    for x in range(vertex_count):
        color = (float_read(buffer,offset)/255, float_read(buffer,offset+0x4)/255,
        float_read(buffer,offset+0x8)/255, float_read(buffer,offset+0xC)/255)
        
        list.append(color)
        offset += 0x10
        if offset >= sector_size:
            return


def get_vert_weights(buffer, offset, sector_size, vertex_count, list):
    for x in range(vertex_count):
        influence_count = int32_read(buffer, offset)
        
        if influence_count > 6:
            print(f"vert {x} influence is over 6!! offset: {hex(offset)}")
            return
        
        offset += 0x4
        vert_group = []
        for f in range(influence_count):
            bone_id = int32_read(buffer, offset)
            weight = float_read(buffer,offset+0x4) / 100 # influence in the format is 0-100, blender is 0-1
            vert_group.append({
                "bone_index"  : bone_id, 
                "bone_weight" : weight})
            offset += 0x8
        list.append(vert_group)
        
        
        if offset >= sector_size:
            return


def get_mesh_attributes(buffer, offset):
    offset -= 0xC
    
    return {
    "AMO_RenderDistance" : int32_read(buffer, offset + 0x0C),
    "AMO_Unknown_0x10"   : int32_read(buffer, offset + 0x10),
    "AMO_Unknown_0x14"   : int32_read(buffer, offset + 0x14),
    "AMO_Culling"        : int32_read(buffer, offset + 0x18),
    "AMO_Scissor"        : int32_read(buffer, offset + 0x1C),
    "AMO_Light"          : int32_read(buffer, offset + 0x20),
    "AMO_Unknown_0x24"   : int32_read(buffer, offset + 0x24),
    "AMO_UVScroll"       : int32_read(buffer, offset + 0x28),
    "AMO_Unknown_0x2C"   : int32_read(buffer, offset + 0x2C),
    "AMO_FadeColor"      : int32_read(buffer, offset + 0x30),
    "AMO_Special"        : int32_read(buffer, offset + 0x34),
    "AMO_Unknown_0x38"   : int32_read(buffer, offset + 0x38),
    "AMO_Unknown_0x3C"   : int32_read(buffer, offset + 0x3C),
    "AMO_Unknown_0x40"   : int32_read(buffer, offset + 0x40),
    "AMO_Unknown_0x44"   : int32_read(buffer, offset + 0x44),
    "AMO_Unknown_0x48"   : int32_read(buffer, offset + 0x48),
    "AMO_Unknown_0x4C"   : int32_read(buffer, offset + 0x4C),
    "AMO_Unknown_0x50"   : int32_read(buffer, offset + 0x50)
    }


def get_mesh_bounding_data(buf, offset, scale):
    return (float_read(buf, offset)*scale, float_read(buf, offset+0x4)*scale,float_read(buf, offset+0x8)*scale, float_read(buf, offset+0xC)*scale)


def build_mesh(all_materials_list, index, filename, mesh_data, striplength):
    mesh_name = f"{filename[:-4]}_mesh{index}" 
    target_mesh = bpy.data.meshes.new(mesh_name)
    created_mesh = bpy.data.objects.new(mesh_name, target_mesh)
    bpy.context.scene.collection.objects.link(created_mesh)

    # adding material to object
    for mat_index in mesh_data["materials"]:
        for mat in all_materials_list:
            testname = mat.name.split("_")[-1][3:]
            if '.' in testname: #duplicate material
                testname = testname.split(".")[0]
            if testname == str(mat_index):
                target_mesh.materials.append(mat)
    
    # set vertices
    bm = bmesh.new()
    for i in range(len(mesh_data["vertices"])):
        vert = bm.verts.new(mesh_data["vertices"][i])
    bm.to_mesh(target_mesh)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    
    # set face indices
    for vertex_index in mesh_data["indices"]:
        triangle_index = vertex_index
        try:
            face = bm.faces.new((bm.verts[triangle_index[0]], bm.verts[triangle_index[1]], bm.verts[triangle_index[2]]))
            face.smooth = True
        except:
            print(f"invalid face: face = bm.faces.new((bm.verts[{triangle_index[0]}], bm.verts[{triangle_index[1]}], bm.verts[{triangle_index[2]}]))")
        
    
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    # set UVs
    uv_layer = bm.loops.layers.uv.new()
    for face in bm.faces:
        for loop in face.loops:
            try:
                loop[uv_layer].uv = mesh_data["UVs"][loop.vert.index]
            except:
                print(f"invalid UV: loop[uv_layer].uv = vertUVs[{loop.vert.index}] // vertcount={len(bm.verts)}")
                continue

    
    # make "material per face" list from original "per strip" list
    face_material_list = []
    loop_index = 0
    for material_index in mesh_data["material_indices"]:
        for x in range(striplength[loop_index]):
            face_material_list.append(material_index)
        loop_index += 1
    
    # set materials of each face
    for face in bm.faces:
        material = face_material_list[face.index]
        face.material_index = material

    # set vertex groups
    if len(mesh_data["weights"]) != 0:
        deform_layer = bm.verts.layers.deform.verify()
        for vert in bm.verts:
            for group in mesh_data["weights"][vert.index]:
                vert_group_name = str(group["bone_index"])
                vert_group_influence = group["bone_weight"]
                mesh_group = created_mesh.vertex_groups.get(vert_group_name) or created_mesh.vertex_groups.new(name=vert_group_name)
                vert[deform_layer][mesh_group.index] = vert_group_influence
    
    # pass bmesh to mesh data
    bm.to_mesh(target_mesh)
    bm.free()
    
    # set custom normals off import normal data
    target_mesh.normals_split_custom_set_from_vertices(mesh_data["normals"])
    
    # set vertex colors
    col_attribute = created_mesh.data.color_attributes.new( name="vertex_color", type='FLOAT_COLOR', domain='POINT',)
    for vertex_index in range(len(created_mesh.data.vertices)):
        col_attribute.data[vertex_index].color = mesh_data["colors"][vertex_index]

    # set mesh attributes
    if len(mesh_data["attributes"]):
        created_mesh.data.AMO_RenderDistance = mesh_data["attributes"]["AMO_RenderDistance"]
        created_mesh.data.AMO_Unknown_0x10   = mesh_data["attributes"]["AMO_Unknown_0x10"]
        created_mesh.data.AMO_Unknown_0x14   = mesh_data["attributes"]["AMO_Unknown_0x14"]
        created_mesh.data.AMO_Culling        = mesh_data["attributes"]["AMO_Culling"]
        created_mesh.data.AMO_Scissor        = mesh_data["attributes"]["AMO_Scissor"]
        created_mesh.data.AMO_Light          = mesh_data["attributes"]["AMO_Light"]
        created_mesh.data.AMO_Unknown_0x24   = mesh_data["attributes"]["AMO_Unknown_0x24"]
        created_mesh.data.AMO_UVScroll       = mesh_data["attributes"]["AMO_UVScroll"]
        created_mesh.data.AMO_Unknown_0x2C   = mesh_data["attributes"]["AMO_Unknown_0x2C"]
        created_mesh.data.AMO_FadeColor      = mesh_data["attributes"]["AMO_FadeColor"]
        created_mesh.data.AMO_Special        = mesh_data["attributes"]["AMO_Special"]
        created_mesh.data.AMO_Unknown_0x38   = mesh_data["attributes"]["AMO_Unknown_0x38"]
        created_mesh.data.AMO_Unknown_0x3C   = mesh_data["attributes"]["AMO_Unknown_0x3C"]
        created_mesh.data.AMO_Unknown_0x40   = mesh_data["attributes"]["AMO_Unknown_0x40"]
        created_mesh.data.AMO_Unknown_0x44   = mesh_data["attributes"]["AMO_Unknown_0x44"]
        created_mesh.data.AMO_Unknown_0x48   = mesh_data["attributes"]["AMO_Unknown_0x48"]
        created_mesh.data.AMO_Unknown_0x4C   = mesh_data["attributes"]["AMO_Unknown_0x4C"]
        created_mesh.data.AMO_Unknown_0x50   = mesh_data["attributes"]["AMO_Unknown_0x50"]
    
    if len(mesh_data["bounding"]) > 0:
        created_mesh.data.AMO_HasBounding = True
        created_mesh.data.AMO_Bounding = mesh_data["bounding"]
    
    return created_mesh


def amo_read(filebuffer, filepath, use_z_up, user_scale):
    filename = os.path.basename(filepath)
    read_offset = 0x0
    created_objects = []
    
    start_sector = get_sector_info(filebuffer, 0x0)
    unknown_sector = get_sector_info(filebuffer, 0xC)
    
    if start_sector["header"] != sector_types["Magic"]:
        print("Magic sector missing from model file.")
        return []
    if unknown_sector["header"] != sector_types["Unknown0002"]:
        print("Unknown sector (0x20000) missing from model file.")
        return []

    read_offset = 0xC + unknown_sector["data_size"]
    model_container = get_sector_info(filebuffer, read_offset)
    
    if model_container["header"] == sector_types["ModelHeader"]:
        all_materials_list = build_materials(filename, filebuffer, read_offset, model_container["data_size"])
        read_offset += 0xC # skip over the model container header
        for model_index in range(model_container["data_count"]):
            
            mesh_sector = get_sector_info(filebuffer, read_offset)
            read_offset += 0xC # skip over mesh sector container header
            
            strip_length_list     = []
            mesh_indices          = []
            mesh_materials        = []
            mesh_vertex_materials = []
            mesh_vertex_coords    = []
            mesh_vertex_normals   = []
            mesh_vertex_UVs       = []
            mesh_vertex_colors    = []
            mesh_vertex_weights   = []
            mesh_bounding_data    = ()
            mesh_attributes       = {}
            
            for s in range(mesh_sector["data_count"]):
                
                current_sector = get_sector_info(filebuffer, read_offset)
                read_offset += 0xC
                
                if current_sector["header"] == sector_types.get("TriStripContainer"):
                    # get strips from all tristrips sectors if it has both or just one
                    for x in range(current_sector["data_count"]):
                        # there's a sector used for regular tri strips (0x0003)
                        # and then there's another version (0x0004) that has strips that index vertices which
                        # are influenced by more than one bone
                        # i haven't noticed any other variations in either giogio or auto modellista
                        strip_sector = get_sector_info(filebuffer, read_offset)
                        get_indices(filebuffer, read_offset, strip_sector["data_count"], mesh_indices, strip_length_list)
                        read_offset += strip_sector["data_size"]
                    continue

                if current_sector["header"] == sector_types.get("MeshMaterialList"): # materials used by the mesh
                    for x in range(current_sector["data_count"]):
                        material_index = int32_read(filebuffer, read_offset)
                        mesh_materials.append(material_index)
                        read_offset += 0x4
                    continue

                if current_sector["header"] == sector_types.get("MaterialIndices"):
                    for x in range(current_sector["data_count"]): # materials per triangle strip
                        material_index = int32_read(filebuffer, read_offset)
                        mesh_vertex_materials.append(material_index)
                        read_offset += 0x4
                    continue

                if current_sector["header"] == sector_types.get("VertexCoordinates"):
                    get_vert_coords(filebuffer, read_offset, read_offset+current_sector["data_size"], 
                                    current_sector["data_count"], mesh_vertex_coords, user_scale, use_z_up)

                if current_sector["header"] == sector_types.get("VertexNormals"):
                    get_vert_normals(filebuffer, read_offset, read_offset+current_sector["data_size"], 
                                    current_sector["data_count"], mesh_vertex_normals, use_z_up)

                if current_sector["header"] == sector_types.get("VertexUVs"):
                    get_vert_uvs(filebuffer, read_offset, read_offset+current_sector["data_size"], 
                                    current_sector["data_count"], mesh_vertex_UVs)
                    
                if current_sector["header"] == sector_types.get("VertexColors"):
                    get_vert_colors(filebuffer, read_offset, read_offset+current_sector["data_size"], 
                                    current_sector["data_count"], mesh_vertex_colors)
                    
                if current_sector["header"] == sector_types.get("VertexWeights"):
                    get_vert_weights(filebuffer, read_offset, read_offset+current_sector["data_size"], 
                                    current_sector["data_count"], mesh_vertex_weights)
                
                if current_sector["header"] == sector_types.get("Attributes"):
                    mesh_attributes = get_mesh_attributes(filebuffer, read_offset)
                
                if current_sector["header"] == sector_types.get("BoundingBox"):
                    mesh_bounding_data = get_mesh_bounding_data(filebuffer, read_offset, user_scale)
            
                read_offset += current_sector["data_size"] - 0xC

            mesh_data = {
            "indices"          : mesh_indices,
            "materials"        : mesh_materials, 
            "material_indices" : mesh_vertex_materials, 
            "vertices"         : mesh_vertex_coords, 
            "normals"          : mesh_vertex_normals, 
            "UVs"              : mesh_vertex_UVs, 
            "colors"           : mesh_vertex_colors,
            "weights"          : mesh_vertex_weights,
            "attributes"       : mesh_attributes,
            "bounding"         : mesh_bounding_data}
            
            created_objects.append(
                build_mesh(all_materials_list, model_index, filename, mesh_data, strip_length_list)
                )

    return created_objects


def read(context, filepath, use_z_up, user_scale): #, use_some_setting
    input_file = open(filepath, 'rb')
    input_file_bytes = input_file.read()
    input_file.close()
    amo_read(input_file_bytes, filepath, use_z_up, user_scale)
    return {'FINISHED'}