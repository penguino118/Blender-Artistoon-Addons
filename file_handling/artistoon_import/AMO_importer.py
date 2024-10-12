import bpy
import os
import bmesh
import math
import mathutils
from ..sector_handler import AMO_sector_dict as sector_type_dict
from ..binary_rw import int16_read, int32_read, float_read

def get_sector_type(buffer, offset):
    head = int32_read(buffer, offset)
    #print(head)
    if head in sector_type_dict:
        return sector_type_dict[head]
    else:
        return f"unsupported sector : {head} at offset {offset}"


def get_sector_header(buffer, offset):
    head = get_sector_type(buffer, offset)
    count = int32_read(buffer, offset+4)
    size = int32_read(buffer, offset+8)
    return [head, count, size]


def print_sector(sector):
    if len(sector) < 3:
        print("invalid sector!! size under 3")
    print(f"Sector Type: {sector[0]}, Data Count: {sector[1]}, Size: {sector[2]}")


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
    offset += material_offset_start
    material_properties = get_sector_header(buffer, offset)
    
    texture_property_list = []
    material_property_list = []
    
    # read through material entries
    if material_properties[0] == "AMO_material_properties":
        print_sector(material_properties)
        offset += 0xC
        for x in range(material_properties[1]):
            material_type = int32_read(buffer, offset)
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
    texture_properties = get_sector_header(buffer, offset)
    if texture_properties[0] == "AMO_texture_properties":
        print_sector(texture_properties)
        offset += 0xC
        for x in range(texture_properties[1]):
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


def get_indices(buffer, offset, sector_size, strip_count, list, strip_length_list):
    offset += 0xC
    for x in range(strip_count):
        count = int16_read(buffer, offset)
        offset += 0x2
        cull_mode = int16_read(buffer, offset) #useless for now
        offset += 0x2
        strip_length_list.append(count-2)
        tmpstrip = []
        for y in range(count):
            vert_index = int32_read(buffer, offset)
            offset += 0x4
            tmpstrip.append(vert_index)  
        for y in range(len(tmpstrip)-2):
            if (y % 2) == 0:
                list.append([tmpstrip[y], tmpstrip[y+1], tmpstrip[y+2]])
            else:
                list.append([tmpstrip[y], tmpstrip[y+2], tmpstrip[y+1]])     
        if offset >= sector_size:
            return


def get_vert_coords(buffer, offset, sector_size, vertex_count, list, scale, use_z_up):
    rotation = mathutils.Euler((math.radians(90.0), 0.0, 0.0), 'XYZ')
    for x in range(vertex_count):
        vertpos = mathutils.Vector((float_read(buffer, offset)*scale, float_read(buffer, offset+0x4)*scale, float_read(buffer, offset+0x8)*scale))
        if use_z_up: vertpos.rotate(rotation)
        list.append(vertpos)
        offset += 0xC
        if offset >= sector_size:
            return


def get_vert_normals(buffer, offset, sector_size, vertex_count, list, use_z_up):
    rotation = mathutils.Euler((math.radians(90.0), 0.0, 0.0), 'XYZ')
    for x in range(vertex_count):
        normal = mathutils.Vector((float_read(buffer, offset), float_read(buffer, offset+0x4), float_read(buffer, offset+0x8)))
        if use_z_up: normal.rotate(rotation)
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


def get_vert_groups(buffer, offset, sector_size, vertex_count, list):
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


def build_mesh(collection, all_materials_list, index, filename, mesh_data, striplength):
    mesh_name = f"{filename[:-4]}_mesh{index}" 
    target_mesh = bpy.data.meshes.new(mesh_name)
    created_mesh = bpy.data.objects.new(mesh_name, target_mesh)
    collection.objects.link(created_mesh)
    
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
        except:
            print(f"invalid face: face = bm.faces.new((bm.verts[{triangle_index[0]}], bm.verts[{triangle_index[1]}], bm.verts[{triangle_index[2]}]))")
        face.smooth = True
    
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
    
    print(f"material={face_material_list}")
    # set materials of each face
    for face in bm.faces:
        material = face_material_list[face.index]
        print(face.index, end="")
        face.material_index = material
    print("\n\n\n")
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


def amo_read(filebuffer, filename, use_z_up, scale):
    sector = get_sector_header(filebuffer, 0x0)
    read_offset = 0
    if sector[0] != "AMO_magic":
        print(f"magic sect missing 0x0\n{sector[0]}")
        return
    else:
        sector = get_sector_header(filebuffer, 0xC)
        if sector[0] != "AMO_unknown":
            print(f"unknown sect missing 0xC\n{sector[0]}")
            return
        else:
            read_offset = 0xC + sector[2]
            
    model_container = get_sector_header(filebuffer, read_offset)
    if model_container[0] != "AMO_model_container":
        print(f"model container missing, offset: {read_offset}")
        return
    else:
        collection_name = f"{filename[:-4]}"
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
        all_materials_list = build_materials(filename, filebuffer, read_offset, model_container[2])
        read_offset += 0xC
        model_count = model_container[1]
        for model_index in range(model_count):
            
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
            
            print(f"model index: {model_index} // read offset: {hex(read_offset)}")
            sector_data_count = int32_read(filebuffer, read_offset+0x4)
            read_offset += 0xC
            
            for sector in range(sector_data_count):
                main_sector = get_sector_header(filebuffer, read_offset)
                print_sector(main_sector)
                
                if main_sector[0] == "AMO_tristrip_container":    
                    strip_count = main_sector[1]
                    read_offset += 0xC
                    for strip_index in range(strip_count):
                        strip_sector =  get_sector_header(filebuffer, read_offset)
                        print_sector(strip_sector)
                        get_indices(filebuffer, read_offset, read_offset+strip_sector[2], strip_sector[1], mesh_indices, strip_length_list)
                        read_offset += strip_sector[2]
                
                elif main_sector[0] == "AMO_material_list":
                    read_offset += 0xC
                    for x in range(main_sector[1]):
                        mat = int32_read(filebuffer, read_offset)
                        mesh_materials.append(mat)
                        read_offset += 0x4
                
                elif main_sector[0] == "AMO_material_per_strip":
                    read_offset += 0xC
                    for x in range(main_sector[1]):
                        mat = int32_read(filebuffer, read_offset)
                        print(f"matread={mat}")
                        mesh_vertex_materials.append(mat)
                        read_offset += 0x4
                
                elif main_sector[0] == "AMO_vertex_coordinates":
                    get_vert_coords(filebuffer, read_offset+0xC, read_offset+main_sector[2], main_sector[1], mesh_vertex_coords, scale, use_z_up)
                    read_offset += main_sector[2]
                
                elif main_sector[0] == "AMO_vertex_normals":
                    get_vert_normals(filebuffer, read_offset+0xC, read_offset+main_sector[2], main_sector[1], mesh_vertex_normals, use_z_up)
                    read_offset += main_sector[2]
                
                elif main_sector[0] == "AMO_vertex_UVs":
                    get_vert_uvs(filebuffer, read_offset+0xC, read_offset+main_sector[2], main_sector[1], mesh_vertex_UVs)
                    read_offset += main_sector[2]
                
                elif main_sector[0] == "AMO_vertex_colors":
                    get_vert_colors(filebuffer, read_offset+0xC, read_offset+main_sector[2], main_sector[1], mesh_vertex_colors)
                    read_offset += main_sector[2]
                
                elif main_sector[0] == "AMO_vertex_groups":
                    get_vert_groups(filebuffer, read_offset+0xC, read_offset+main_sector[2], main_sector[1], mesh_vertex_weights)
                    read_offset += main_sector[2]
                
                elif main_sector[0] == "AMO_mesh_attributes":
                    mesh_attributes = get_mesh_attributes(filebuffer, read_offset+0xC)
                    read_offset += main_sector[2]

                elif main_sector[0] == "AMO_hitbox_identifier":
                    mesh_bounding_data = get_mesh_bounding_data(filebuffer, read_offset+0xC, scale)
                    read_offset += main_sector[2] #todo
                
                elif main_sector[0] == "AMO_unused_unknown":
                    #completely unused sector, don't know the purpose, never called by GetSubDataAMO 
                    read_offset += main_sector[2]
                
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
            
            build_mesh(collection, all_materials_list, model_index, filename, mesh_data, strip_length_list)


def read(context, filepath, use_z_up, scale): #, use_some_setting
    input_file = open(filepath, 'rb')
    input_file_bytes = input_file.read()
    input_file.close()
    filename = os.path.basename(filepath)
    amo_read(input_file_bytes, filename, use_z_up, scale)
    return {'FINISHED'}