import bpy
import os
import struct
import bmesh
import math
import mathutils

bl_info = {
    "name": "Artistoon Model Importer",
    "description": "Importer for the Artistoon Model Format (AMO) found in GioGio's Bizarre Adventure.",
    "author": "Penguino",
    "version": (1, 0),
    "blender": (3, 6, 1),
    "location": "File > Import",
    "warning": "", # used for warning icon and text in addons panel
    "category": "Import",
}

sector_type_dict = {
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
    0x000F0000 : "AMO_mesh_attributes",     #PlAMOGetModelAttributes
    0x00110000 : "AMO_hitbox_identifier",   #bounding model fetch, used for stages
    0x00000009 : "AMO_material_properties", #global
    0x0000000A : "AMO_texture_properties"
    }

model_type_dict = { #######where are materials 2 and 4 ?????
    0x00000000 : "VFX",       #eff00.pzz meshes
    0x00000001 : "CelShaded",
    0x00000003 : "Shadeless", #used on transparent meshes
    0x00000005 : "Static"     #loading screens, stage objects, etc
    }

def int16_read(buf, offset):
    return struct.unpack("<H", buf[offset:offset+2])[0]

def int32_read(buf, offset):
    return struct.unpack("<I", buf[offset:offset+4])[0]

def float_read(buf, offset):
    return struct.unpack("<f", buf[offset:offset+4])[0]

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

def create_material(filename, index, material_type, texture_index, material_list, material_property):
    material_name = f"{filename[:-4]}_mat{index}"
    material = bpy.data.materials.new(material_name) 
    material_list.append(material)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    
    print(material_property)
    unkproperty1 = material_property[index][1]
    unkproperty2 = material_property[index][2]
    unkproperty3 = material_property[index][3]
    unkproperty4 = material_property[index][4]
    unkproperty5 = material_property[index][5]
    
    material['mat_type'] = material_property[index][0]
    material['unknown_1'] = unkproperty1
    material['unknown_2'] = unkproperty2
    material['unknown_3'] = unkproperty3
    material['unknown_4'] = unkproperty4
    material['unknown_5'] = unkproperty5
    material['tex_image'] = material_property[index][6]
    
    #bsdf = 
    if nodes.get("Principled BSDF") != None:
        nodes.remove(nodes.get("Principled BSDF"))
    
    #material_output = nodes.get("ShaderNodeOutputMaterial")
    #print(material_output)
    material_output = nodes.get("Material Output") 
    imgnode = nodes.new('ShaderNodeTexImage')
    imgnode.image = bpy.data.images.get(f"{filename[:-4]}_tex{texture_index}")
    
    links = material.node_tree.links
    
    #print(imgnode.inputs)
    #print(nodes.get("Mix"))
    if material_type == "CelShaded":
        diffuse = nodes.new('ShaderNodeBsdfDiffuse')
        specular = nodes.new('ShaderNodeBsdfDiffuse')
        
        difframpnode = nodes.new('ShaderNodeValToRGB')
        specrampnode = nodes.new('ShaderNodeValToRGB')
        
        difftorgbnode = nodes.new('ShaderNodeShaderToRGB')
        spectorgbnode = nodes.new('ShaderNodeShaderToRGB')
        
        multcolmixnode = nodes.new('ShaderNodeMixRGB')
        multdifmixnode = nodes.new('ShaderNodeMixRGB')
        screenmixnode = nodes.new('ShaderNodeMixRGB')
        
        colnode = nodes.new('ShaderNodeVertexColor')
        
        #diffuse color ramp
        #[0] - 0.00 - #CECECE
        #[1] - 0.38 - #BABABA
        #[2] - 0.50 - #FFFFFF
        #[3] - 1.00 - #FFFFFF
        
        #spec color ramp
        #[0] - 0.00 - #000000
        #[1] - 0.95 - col= 0.60
        
        difframpnode.location    = (-124, 828)
        specrampnode.location    = (-132, 588)
        diffuse.location         = (-574, 808)
        difftorgbnode.location   = (-346, 800)
        spectorgbnode.location   = (-346, 557)
        specular.location        = (-574, 565)
        specrampnode.location    = (-346, 556)
        colnode.location         = (-360, 280)
        multcolmixnode.location  = ( -39, 327)
        multdifmixnode.location  = ( 215, 333)
        screenmixnode.location   = ( 493, 363)
        imgnode.location         = (-459, 150)
        material_output.location = ( 713, 380)
        
        #multcolmixnode.data_type = 'RGBA'
        multcolmixnode.blend_type = 'MULTIPLY'
        multcolmixnode.inputs[0].default_value = 1.000
        
        #multdifmixnode.data_type = 'RGBA'
        multdifmixnode.blend_type = 'MULTIPLY'
        multdifmixnode.inputs[0].default_value = 1.000
        
        #screenmixnode.data_type = 'RGBA'
        screenmixnode.blend_type = 'SCREEN'
        screenmixnode.inputs[0].default_value = 1.000
        
        difframpnode.color_ramp.interpolation = 'CONSTANT'
        difframpnode.color_ramp.elements[0].color = (0.60, 0.60, 0.60, 1.00)
        
        difframpnode.color_ramp.elements.new(0.38)
        difframpnode.color_ramp.elements[1].color = (0.50, 0.50, 0.50, 1.00)
        
        difframpnode.color_ramp.elements.new(0.50)
        difframpnode.color_ramp.elements[2].color = (1.00, 1.00, 1.00, 1.00)
        
        specrampnode.color_ramp.interpolation = 'CONSTANT'
        specrampnode.color_ramp.elements[0].color = (0.00, 0.00, 0.00, 0.00)
        specrampnode.color_ramp.elements.new(0.95)
        specrampnode.color_ramp.elements[1].color = (0.60, 0.60, 0.60, 1.00)
        
        #links.new(multcolmixnode.inputs[1], colnode.outputs[0])
        #links.new(multcolmixnode.inputs[2], imgnode.outputs[0])
        
        links.new(diffuse.outputs['BSDF'],  difftorgbnode.inputs['Shader'])
        links.new(specular.outputs['BSDF'], spectorgbnode.inputs['Shader'])
        
        links.new(difftorgbnode.outputs['Color'],  difframpnode.inputs['Fac'])
        links.new(spectorgbnode.outputs['Color'],  specrampnode.inputs['Fac'])
        
        links.new(colnode.outputs['Color'], multcolmixnode.inputs['Color1'])
        links.new(imgnode.outputs['Color'], multcolmixnode.inputs['Color2'])
        
        links.new(multcolmixnode.outputs['Color'], multdifmixnode.inputs['Color1'])
        links.new(difframpnode.outputs['Color'], multdifmixnode.inputs['Color2'])
        
        links.new(specrampnode.outputs['Color'], screenmixnode.inputs['Color1'])
        links.new(multdifmixnode.outputs['Color'], screenmixnode.inputs['Color2'])
        
        links.new(screenmixnode.outputs['Color'], material_output.inputs['Surface'])
        
    else:
        imgnode.location = (-350, 350)
        links.new(material_output.inputs['Surface'], imgnode.outputs[0])
    return
    
def create_textures(filename, texlist):
    for x in range(len(texlist)):
        tex_index  = texlist[x][0]
        tex_width  = texlist[x][1]
        tex_height = texlist[x][2]
        texture_name = f"{filename[:-4]}_tex{x}"
        texture = bpy.data.textures.new(texture_name, 'IMAGE')
        texture['img_index']  = tex_index
        texture['tex_width']  = tex_width
        texture['tex_height'] = tex_height

def build_materials(filename, buffer, offset, material_start, material_list):
    print("Building materials...")
    offset += material_start
    material_properties = get_sector_header(buffer, offset)
    mat_property = []
    tmp_mat_list = []
    tmp_tex_list = []
    if material_properties[0] == "AMO_material_properties":
        print_sector(material_properties)
        offset += 0xC
        print(filename)
        for x in range(material_properties[1]):
            type_test = int32_read(buffer, offset)
            
            unk1 = float_read(buffer, offset+0x0C), float_read(buffer, offset+0x10), float_read(buffer, offset+0x14), float_read(buffer, offset+0x18)
            unk2 = float_read(buffer, offset+0x1C), float_read(buffer, offset+0x20), float_read(buffer, offset+0x24), float_read(buffer, offset+0x28)
            unk3 = float_read(buffer, offset+0x2C), float_read(buffer, offset+0x30), float_read(buffer, offset+0x34), float_read(buffer, offset+0x38)
            unk4 = float_read(buffer, offset+0x3C)
            unk5 = int32_read(buffer, offset+0x40)
            texture = int32_read(buffer, offset+0x10C)
            
            mat_property.append([type_test, unk1, unk2, unk3, unk4, unk5, texture])
            mat_skip = int32_read(buffer, offset+0x8)
            print(f"typetest= {type_test} // matskip = {mat_skip}")
            if type_test in model_type_dict:
                model_type = model_type_dict[type_test]
            else:
                model_type = "Shadeless"
            tmp_mat_list.append(model_type)
            offset += mat_skip
            #bpy.ops.material.new()
        #offset += material_properties[2]
    
    texture_properties = get_sector_header(buffer, offset)
    if texture_properties[0] == "AMO_texture_properties":
        print_sector(texture_properties)
        offset += 0xC
        for x in range(texture_properties[1]):
            buf_skip = int32_read(buffer, offset+0x8)
            tex_index  = int32_read(buffer, offset+0xC)
            tex_width  = int32_read(buffer, offset+0x10)
            tex_height = int32_read(buffer, offset+0x14)
            tmp_tex_list.append([tex_index, tex_width, tex_height])
            mat_type = tmp_mat_list[x]
            create_material(filename, x, mat_type, tex_index, material_list, mat_property)
            offset += buf_skip
        create_textures(filename, tmp_tex_list)
        

def get_indices(buffer, offset, sector_size, strip_count, list, tmp_strip_length):
    offset += 0xC
    for x in range(strip_count):
        count = int16_read(buffer, offset)
        offset += 0x2
        cull_mode = int16_read(buffer, offset) #useless for now
        offset += 0x2
        tmp_strip_length.append(count-2)
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

def get_vert_coords(buffer, offset, sector_size, vertex_count, list):
    for x in range(vertex_count):
        #if upflag:
        #    vertpos = float_read(buffer, offset), float_read(buffer, offset+0x8), float_read(buffer, offset+0x4)
        #else:
        vertpos = float_read(buffer, offset), float_read(buffer, offset+0x4), float_read(buffer, offset+0x8)
        list.append(vertpos)
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
            weight = float_read(buffer,offset+0x4)/100
            vert_group.append((bone_id, weight))
            offset += 0x8
        list.append(vert_group)
        
        
        if offset >= sector_size:
            return

def get_mesh_attributes(buffer, offset, sector_size, list):
    offset -= 0xC
    
    attribute_offsets = [
    0x0C, #max render distance
    0x10, #aa_material (dunno what it do lol)
    0x14, 
    0x18, #aa_cull (dunno what it do lol)
    0x1C, #aa_scissor (bool for oclussion culling)
    0x20, #aa_light (set to 2 in transparent meshes)
    0x24, 
    0x28, #aa_uvscroll (...for main menu clouds?)
    0x2C, 
    0x30, #aa_fadecolor (dunno what it do lol) 
    0x34, #aa_special (dunno what it do lol) 
    0x38, 
    0x3C, 
    0x40, 
    0x44, 
    0x48,
    0x4C,
    0x50]
    
    for attribute_offset in attribute_offsets:
        value = int32_read(buffer, offset + attribute_offset)
        list.append(value)
    #print(list)

def get_mesh_hit(buf, offset, count, list):
    for x in range(count):
        unk1 = (int16_read(buf, offset), int16_read(buf, offset+0x2), int16_read(buf, offset+0x4), int16_read(buf, offset+0x6))
        unk2 = (float_read(buf, offset+0x8), float_read(buf, offset+0xC))
        list.append([unk1, unk2])

def build_mesh(collection, index, filename, mesh_data, striplength, upflag):
    indices       = mesh_data[0]
    mat_list      = mesh_data[1]
    mat_per_strip = mesh_data[2]
    vertcoords    = mesh_data[3]
    vertnormals   = mesh_data[4]
    vertUVs       = mesh_data[5]
    vertcolors    = mesh_data[6]
    vertweights   = mesh_data[7]
    attributes    = mesh_data[8]
    hitbox_fetch  = mesh_data[9]
    material_list = mesh_data[10]
    
    mesh_name = f"{filename[:-4]}_mesh{index}" 
    target_mesh = bpy.data.meshes.new(mesh_name)
    created_mesh = bpy.data.objects.new(mesh_name, target_mesh)
    collection.objects.link(created_mesh)
    
    if upflag:
        created_mesh.rotation_euler = (math.radians(90), 0.0, math.radians(180))
    
    for mat_index in mat_list:
        for mat in material_list:
            testname = mat.name.split("_")[-1][3:]
            if '.' in testname: #duplicate material
                testname = testname.split(".")[0]
            if testname == str(mat_index):
                target_mesh.materials.append(mat)
    
    bm = bmesh.new()
    for i in range(len(vertcoords)):
        vert = bm.verts.new(vertcoords[i])
    bm.to_mesh(target_mesh)
    
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    
    for vertex_index in indices:
        triangle_index = vertex_index
        try:
            face = bm.faces.new((bm.verts[triangle_index[0]], bm.verts[triangle_index[1]], bm.verts[triangle_index[2]]))
        except:
            continue
        face.smooth = True
    
    uv_layer = bm.loops.layers.uv.new()
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].uv = vertUVs[loop.vert.index]
    bm.to_mesh(target_mesh)
    
    #strip list to face list
    face_mat_list = []
    loop_index = 0
    for mat in mat_per_strip:
        for x in range(striplength[loop_index]):
            face_mat_list.append(mat)
        loop_index += 1
        
    for face in bm.faces:
        material = face_mat_list[face.index]
        face.material_index = material
    bm.to_mesh(target_mesh)
    
    if len(vertweights) != 0:
        deform_layer = bm.verts.layers.deform.verify()
        for vert in bm.verts:
            for group in vertweights[vert.index]:
                vert_group_name = str(group[0])
                vert_group_influence = group[1]
                mesh_group = created_mesh.vertex_groups.get(vert_group_name) or created_mesh.vertex_groups.new(name=vert_group_name)
                vert[deform_layer][mesh_group.index] = vert_group_influence
        bm.to_mesh(target_mesh)

    if len(attributes) == 18:
        created_mesh.data['aa_render_dist']  = attributes[0]
        created_mesh.data['aa_material']     = attributes[1]
        created_mesh.data['aa_unknown_0x02'] = attributes[2]
        created_mesh.data['aa_cull']         = attributes[3]
        created_mesh.data['aa_scissor']      = attributes[4]
        created_mesh.data['aa_light']        = attributes[5]
        created_mesh.data['aa_unknown_0x06'] = attributes[6]
        created_mesh.data['aa_uvscroll']     = attributes[7]
        created_mesh.data['aa_unknown_0x08'] = attributes[8]
        created_mesh.data['aa_fadecolor']    = attributes[9]
        created_mesh.data['aa_special']      = attributes[0xA]
        created_mesh.data['aa_unknown_0x0B'] = attributes[0xB]
        created_mesh.data['aa_unknown_0x0C'] = attributes[0xC]
        created_mesh.data['aa_unknown_0x0D'] = attributes[0xD]
        created_mesh.data['aa_unknown_0x0E'] = attributes[0xE]
        created_mesh.data['aa_unknown_0x0F'] = attributes[0xF]
        created_mesh.data['aa_unknown_0x10'] = attributes[0x10]
        created_mesh.data['aa_unknown_0x11'] = attributes[0x11]
    
    for x in range(len(hitbox_fetch)):
        created_mesh.data[f'bounding_{x}_unk1'] = hitbox_fetch[x][0]
        created_mesh.data[f'bounding_{x}_unk2'] = hitbox_fetch[x][1]
    
    loop_normals = []
    for l in target_mesh.loops:
        loop_normals.append(vertnormals[l.vertex_index])
    target_mesh.normals_split_custom_set(loop_normals)
    target_mesh.use_auto_smooth = True

    col_attribute = created_mesh.data.color_attributes.new(
    name="vertex_color",
    type='FLOAT_COLOR',
    domain='POINT',
    )
    cols = []
    for v_index in range(len(created_mesh.data.vertices)):
        cols += vertcolors[v_index]
    col_attribute.data.foreach_set("color", cols)

    bm.free()

def amo_read(filedata, filepath, upflag):
    filebuffer = filedata
    filename = os.path.basename(filepath)
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
        model_materials = []
        build_materials(filename, filebuffer, read_offset, model_container[2], model_materials)
        read_offset += 0xC
        model_count = model_container[1]
        for model_index in range(model_count):
            
            tmp_strip_length      = []
            mesh_indices          = []
            mesh_materials        = []
            mesh_vertex_materials = []
            mesh_vertex_coords    = []
            mesh_vertex_normals   = []
            mesh_vertex_UVs       = []
            mesh_vertex_colors    = []
            mesh_vertex_weights   = []
            mesh_hitbox_fetch     = []
            mesh_attributes       = []
            
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
                        get_indices(filebuffer, read_offset, read_offset+strip_sector[2], strip_sector[1], mesh_indices, tmp_strip_length)
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
                        mesh_vertex_materials.append(mat)
                        read_offset += 0x4
                
                elif main_sector[0] == "AMO_vertex_coordinates":
                    get_vert_coords(filebuffer, read_offset+0xC, read_offset+main_sector[2], main_sector[1], mesh_vertex_coords)
                    read_offset += main_sector[2]
                
                elif main_sector[0] == "AMO_vertex_normals":
                    get_vert_coords(filebuffer, read_offset+0xC, read_offset+main_sector[2], main_sector[1], mesh_vertex_normals)
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
                    get_mesh_attributes(filebuffer, read_offset+0xC, read_offset+main_sector[2], mesh_attributes)
                    read_offset += main_sector[2]

                elif main_sector[0] == "AMO_hitbox_identifier":
                    get_mesh_hit(filebuffer, read_offset+0xC, main_sector[1], mesh_hitbox_fetch)
                    read_offset += main_sector[2] #todo
                
            mesh_data = [
            mesh_indices,
            mesh_materials, 
            mesh_vertex_materials, 
            mesh_vertex_coords, 
            mesh_vertex_normals, 
            mesh_vertex_UVs, 
            mesh_vertex_colors,
            mesh_vertex_weights,
            mesh_attributes,
            mesh_hitbox_fetch,
            model_materials
            ]
            build_mesh(collection, model_index, filename, mesh_data, tmp_strip_length, upflag)


def read_some_data(context, filepath, upflag): #, use_some_setting
    print("running read_some_data...")
    f = open(filepath, 'rb')
    data = f.read()
    f.close()

    # would normally load the data here
    amo_read(data, filepath, upflag)

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ImportSomeData(Operator, ImportHelper):
    """Import Artistoon Model data as a new collection."""
    bl_idname = "import_scene.amo"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Artistoon Model"

    # ImportHelper mixin class uses this
    filename_ext = ".amo"

    filter_glob: StringProperty(
        default="*.amo",
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
        return read_some_data(context, self.filepath, self.z_up) # self.use_setting


# Only needed if you want to add into a dynamic menu.
def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="Artistoon Model (.amo)")


# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access).
def register():
    bpy.utils.register_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_scene.amo('INVOKE_DEFAULT')
