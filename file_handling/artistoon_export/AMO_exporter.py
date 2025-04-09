import bpy
import math
import bmesh
import mathutils
from ..util import all_equal, flip_yz, natural_keys
from ..binary_rw import int32_write, float_write, pad_with_byte
from ..sector_handler import insert_header
from ...pyffi.utils import tristrip

def get_all_materials(mesh_objects):
    
    def get_material_name(material):
        return material.name.split('.')[0] # split so duplicate materials are indexed correctly
    
    def get_texture_properties(material):
        return {
        "AMO_TextureIndex" : material.AMO_TextureIndex,
        "AMO_TextureWidth" : material.AMO_TextureWidth,
        "AMO_TextureHeight" : material.AMO_TextureHeight }
    
    output_bytes = bytearray()
    material_list_sector_bytes = bytearray()
    texture_list_sector_bytes = bytearray()
    
    material_name_list = [] # for mesh indices
    material_list = [] # sorted list of materials from all meshes in the collections
    texture_list = [] # texture list generated of textures listed by material properties
    
    # collect all materials in the collections
    for obj in mesh_objects:
        mesh = obj.data
        for material in mesh.materials:
            if material not in material_list:
                # add material's listed texture to texture list
                texture_property = get_texture_properties(material)
                if texture_property not in texture_list:
                    texture_list.append(get_texture_properties(material))
                # setting the material's texture index to be the index of the texture in the texture list
                material["ExportTextureIndex"] = texture_list.index(texture_property)
                material_list.append(material)
    material_list = sorted(material_list, key=get_material_name)
    
    # writing output bytes of material list 
    for material in material_list:
        material_name_list.append(material.name)

        material_list_sector_bytes.extend(int32_write(material.AMO_MaterialType)) # head
        material_list_sector_bytes.extend(int32_write(1)) # count
        material_list_sector_bytes.extend(int32_write(0x110)) # size
        
        for float in material.AMO_ColorUnk1:
            material_list_sector_bytes.extend(float_write(float))
        for float in material.AMO_ColorUnk2:
            material_list_sector_bytes.extend(float_write(float))
        for float in material.AMO_ColorUnk3:
            material_list_sector_bytes.extend(float_write(float))
        
        material_list_sector_bytes.extend(float_write(material.AMO_Unknown4))
        material_list_sector_bytes.extend(int32_write(material.AMO_Unknown5))
        pad_with_byte(material_list_sector_bytes, 0x00, 0xC8)
        material_list_sector_bytes.extend(int32_write(material["ExportTextureIndex"]))
    
    # sector header
    insert_header(material_list_sector_bytes, 0x00000009, len(material_list))
    
    # writing output bytes of texture list 
    for texture in texture_list:
        texture_list_sector_bytes.extend(int32_write(0)) # texture entry head
        texture_list_sector_bytes.extend(int32_write(1)) # count (always one)
        texture_list_sector_bytes.extend(int32_write(0x10C)) # size

        texture_list_sector_bytes.extend(int32_write(texture["AMO_TextureIndex"]))
        texture_list_sector_bytes.extend(int32_write(texture["AMO_TextureWidth"]))
        texture_list_sector_bytes.extend(int32_write(texture["AMO_TextureHeight"]))
        pad_with_byte(texture_list_sector_bytes, 0x00, 0xF4)
    
    # sector header
    insert_header(texture_list_sector_bytes, 0x0000000A, len(texture_list))

    output_bytes.extend(material_list_sector_bytes)
    output_bytes.extend(texture_list_sector_bytes)
    return output_bytes, material_name_list


def get_indices(object, mesh, all_material_names, face_type):

    def write_indices(output_bytes, list):
        for poly in list:
            size = len(poly)
            output_bytes.extend(int32_write(size))
            for vert in poly:
                output_bytes.extend(int32_write(vert))

    def write_materials(face_material_index_list, mesh_material_list, output_bytes):
        for face_material in face_material_index_list:
            for material in mesh_material_list:
                if face_material == material:
                    output_bytes.extend(int32_write(mesh_material_list.index(material)))

    def add_face(split_faces_list, material_name, poly_verts):
        if material_name in split_faces_list:
            split_faces_list[material_name].append(poly_verts)
        else:
            split_faces_list[material_name] = [poly_verts]
    
    def collect_indices(faces, face_type):
        collected_indices = []
        collected_materials = []
        for material, indices in faces: #split_03_faces.items()
            if face_type == 'TRI_STRIP': indices = tristrip.stripify(indices)
            for index in indices:
                collected_indices.append(index)
                collected_materials.append(material)
        return collected_indices, collected_materials

    output_bytes = bytearray()
    complex_verts = []
    mesh_material_list = []

    # giogio stores faces with two or more weight groups on a separate list (04 instead of 03)
    for vert in mesh.vertices: #gather indices for type 04 list
        current_vertex_group = []
        for vert_groups in vert.groups:
            group_name = object.vertex_groups[vert_groups.group].name
            group_weight = vert_groups.weight
            current_vertex_group.append([group_name, group_weight])
        if len(current_vertex_group) > 1: #if more than one group on this vertex add to 04 verts list
            complex_verts.append(vert.index)

    split_03_faces = {} # 03 faces split by material
    split_04_faces = {} # 04 faces split by material
    for poly in mesh.polygons:
        poly_verts = list(poly.vertices)
        
        # add materials to material name list
        material_name = mesh.materials[poly.material_index].name
        if material_name not in mesh_material_list:
            mesh_material_list.append(material_name)
        
        # add faces
        if any(vert in complex_verts for vert in poly_verts): # checking if there's any 04 type verts
            add_face(split_04_faces, material_name, poly_verts)
        else:
            add_face(split_03_faces, material_name, poly_verts)    
    
    indices_03, materials_03 = collect_indices(split_03_faces.items(), face_type) 
    indices_04, materials_04 = collect_indices(split_04_faces.items(), face_type) 

    # add strips to binary
    write_indices(output_bytes, indices_03)
    # insert container header at start
    insert_header(output_bytes, 0x00030000, len(indices_03))
    # attach type 2 indices after if they exist
    if len(indices_04) > 0:
        strip04_bytes = bytearray()
        write_indices(strip04_bytes, indices_04)
        insert_header(strip04_bytes, 0x00040000, len(indices_04))
        output_bytes.extend(strip04_bytes)
    
    # strip container
    strip_sector_count = (len(indices_04) > 0) + (len(indices_03) > 0)
    insert_header(output_bytes, 0x00000005, strip_sector_count)

    # mesh material list 
    material_list_bytes = bytearray()
    material_count = len(mesh_material_list)
    for material in mesh_material_list: 
        material_index = all_material_names.index(material)
        material_list_bytes.extend(int32_write(material_index))
    insert_header(material_list_bytes, 0x00050000, material_count)

    # material per strip
    material_indices_bytes = bytearray()
    total_strip_count = len(indices_03) + len(indices_04)
    write_materials(materials_03, mesh_material_list, material_indices_bytes)
    write_materials(materials_04, mesh_material_list, material_indices_bytes)
    insert_header(material_indices_bytes, 0x00060000, total_strip_count)
    
    # merge
    output_bytes.extend(material_list_bytes)
    output_bytes.extend(material_indices_bytes)
    return output_bytes


def get_vert_coord(mesh, scale, use_z_up):
    output_bytes = bytearray()
    vertex_count = len(mesh.vertices)

    for vert in mesh.vertices:
        vertex_coord = mathutils.Vector([vert.co.xyz[0], vert.co.xyz[1], vert.co.xyz[2]])
        if use_z_up: flip_yz(vertex_coord)
        for coord in vertex_coord:
            output_bytes.extend(float_write(coord*scale))
    
    insert_header(output_bytes, 0x00070000, vertex_count)
    return output_bytes 


def get_vert_normal(mesh, use_z_up):
    output_bytes = bytearray()
    vertex_count = len(mesh.vertices)
    
    for vert in mesh.vertices:
        vertex_normal = mathutils.Vector((vert.normal[0], vert.normal[1], vert.normal[2]))
        if use_z_up: flip_yz(vertex_normal)
        for normal in vertex_normal:
            output_bytes.extend(float_write(normal))
            
    insert_header(output_bytes, 0x00080000, vertex_count)
    return output_bytes 


def get_loop_normal(mesh, use_z_up):
    output_bytes = bytearray()
    vertex_count = len(mesh.vertices)
    
    packed_normals = []
    for loop in mesh.loops:
        packed_normals.append([loop.vertex_index, loop.normal])

    vert_normals = []
    for vert in mesh.vertices:
        vert_index = vert.index
        added_verts = []
        for normal in packed_normals:
            if normal[0] == vert_index and vert_index not in added_verts:
                vert_normals.append(mathutils.Vector((normal[1][0], normal[1][1], normal[1][2]))) # this is because its read only or some shit Whatever I just wanna get it woriking man
                added_verts.append(vert_index)

    for normal in vert_normals:
        if use_z_up: flip_yz(normal)
        for direction in normal:
            output_bytes.extend(float_write(direction))
    
    insert_header(output_bytes, 0x00080000, vertex_count)
    return output_bytes 


def get_vert_UVs(mesh): # todo: GROSS ! ! !
    output_bytes = bytearray()
    vertex_count = len(mesh.vertices)
    
    tmpuv = []
    for face in mesh.polygons:
        for vertindex, loopindex in zip(face.vertices, face.loop_indices):
            uv_coords = mesh.uv_layers.active.data[loopindex].uv
            tmpuv.append([vertindex, uv_coords])
    
    for vert in mesh.vertices:
        vert_index = vert.index
        added_verts = []
        for uv in tmpuv:
            if uv[0] == vert_index and vert_index not in added_verts:
                output_bytes.extend(float_write(uv[1][0]))
                output_bytes.extend(float_write(1.0 - uv[1][1])) # Y is flipped for this format
                added_verts.append(vert_index)
    
    insert_header(output_bytes, 0x000A0000, vertex_count)
    return output_bytes 


def get_vert_color(mesh):
    output_bytes = bytearray()
    vertex_count = len(mesh.vertices)
    color_attribute = mesh.color_attributes.active_color
    
    if color_attribute != None:
        for vertex_color in color_attribute.data:
            red   = vertex_color.color[0] * 255
            green = vertex_color.color[1] * 255
            blue  = vertex_color.color[2] * 255
            alpha = vertex_color.color[3] * 255
            output_bytes.extend(float_write(red))
            output_bytes.extend(float_write(green))
            output_bytes.extend(float_write(blue))
            output_bytes.extend(float_write(alpha))

    insert_header(output_bytes, 0x000B0000, vertex_count)
    return output_bytes


def get_vert_group(object, bone_list):
    def get_group_index(name):
        for i, entry in enumerate(bone_list):
            if name == entry["name"]:
                return i
        return -1
        
    output_bytes = bytearray()
    mesh = object.data
    vertex_count = len(mesh.vertices)

    if len(object.vertex_groups) > 0:
        for vert in mesh.vertices:
            vertex_group_data = []
            for group in vert.groups:
                group_name = object.vertex_groups[group.group].name 
                group_index = get_group_index(group_name)
                #if group_index == -1: continue # grouped to bone not present in armature, BYE!!!
                group_weight = group.weight * 100 # model format weights are in the range 0 - 100
                vertex_group_data.append({
                    "index" : group_index,
                    "weight" : group_weight
                    })
            
            output_bytes.extend(int32_write(len(vertex_group_data))) # count of how many groups influence the current vertex
            for group in vertex_group_data:
                output_bytes.extend(int32_write(group["index"]))
                output_bytes.extend(float_write(group["weight"]))
        
        insert_header(output_bytes, 0x000C0000, vertex_count)
    return output_bytes


def get_attributes(mesh):
    output_bytes = bytearray()

    attributes = [
        mesh.AMO_RenderDistance,
        mesh.AMO_Unknown_0x10,
        mesh.AMO_Unknown_0x14,
        mesh.AMO_Culling,
        mesh.AMO_Scissor,
        mesh.AMO_Light,
        mesh.AMO_Unknown_0x24,
        mesh.AMO_UVScroll,
        mesh.AMO_Unknown_0x2C,
        mesh.AMO_FadeColor,
        mesh.AMO_Special,
        mesh.AMO_Unknown_0x38,
        mesh.AMO_Unknown_0x3C,
        mesh.AMO_Unknown_0x40,
        mesh.AMO_Unknown_0x44,
        mesh.AMO_Unknown_0x48,
        mesh.AMO_Unknown_0x4C,
        mesh.AMO_Unknown_0x50]

    for attribute in attributes:
        output_bytes.extend(int32_write(attribute))

    insert_header(output_bytes, 0x000F0000, 1)
    return output_bytes


def get_bounding(mesh, scale):
    if mesh.AMO_HasBounding == False: return bytearray()
    
    output_bytes = bytearray()
    for float in mesh.AMO_Bounding:
        output_bytes.extend(float_write(float*scale))
    insert_header(output_bytes, 0x00110000, 1)

    return output_bytes


def triangulate_bmesh(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='LONG_EDGE')
    bm.to_mesh(mesh)
    bm.free()


def uv_split_bmesh(mesh): # todo: GROSS !! ! ! !! 
    # the idea: giogio meshes only support one UV per vertex.
    # in blender, a vertex can have many UV coordinates, depending on the connected faces
    # ergo: split faces apart if they cause a vertex to have more than one UV coordinate
    # bad: this is slow and written in a dumb way. but it works
    # also disconnected faces (that could otherwise be connected to tristrips) waste memory
    # PS this applies to normals and vertex colors too, but those are taken care of
 
    bm = bmesh.new()
    bm.from_mesh(mesh)
    
    packed_uv = []
    for face in mesh.polygons:
        for vertindex, loopindex in zip(face.vertices, face.loop_indices):
            uv_coords = mesh.uv_layers.active.data[loopindex].uv
            packed_uv.append([vertindex, uv_coords])

    edges_to_split = []

    for vert in bm.verts:
        
        index = vert.index
        vert_uvs = [uv for uv in packed_uv if index in uv]
        
        if not all_equal(vert_uvs):
            for edge in bm.edges :
                if vert in edge.verts:
                    if edge not in edges_to_split:
                        edges_to_split.append(edge)

    bmesh.ops.split_edges(bm, edges=edges_to_split)
    bm.edges.index_update()
    
    bm.verts.index_update()
    bm.to_mesh(mesh)
    bm.free()


def transfer_normals(source, dest):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects[dest.name].select_set(True)
    bpy.context.view_layer.objects.active = source
    bpy.ops.object.data_transfer(data_type='CUSTOM_NORMAL', loop_mapping='POLYINTERP_NEAREST')
    bpy.ops.object.select_all(action='DESELECT')


def get_amo(mesh_objects, bone_list, uv_split, face_type, normal_type, scale, use_z_up):
    output_bytes = bytearray()
    material_texture_bytes, all_material_names = get_all_materials(mesh_objects)
    mesh_count = len(mesh_objects)
    
    total_sectors_in_file = 1
    # todo: dumb ugly 
    if len(mesh_objects) > 0:
        entry_info = {
        "index" : mesh_objects[0].PZZ_Index,
        "compressed" : mesh_objects[0].PZZ_Compressed}
        total_sectors_in_file += 1
    else:
        entry_info = {
            "index" : -1
        }

    for object in mesh_objects:
        print("Exporting AMO Mesh: ", object.name)
        mesh_data_bytes = bytearray()
        
        edit_object = object.copy() # edit mesh where we will triangulate / uv split
        edit_object.data = object.data.copy()
        edit_object.data.calc_loop_triangles()
        bpy.context.scene.collection.objects.link(edit_object)
        mesh = edit_object.data
        
        triangulate_bmesh(mesh)
        if uv_split:
            uv_split_bmesh(mesh)
            transfer_normals(object, edit_object)
            mesh = edit_object.data
        
        # mesh indices container can have two separate sectors of indices
        mesh_indices = get_indices(edit_object, mesh, all_material_names, face_type)

        vertex_coords  = get_vert_coord(mesh, scale, use_z_up)
        
        if normal_type == 'LOOP_NORMALS':
            vertex_normals = get_loop_normal(mesh, use_z_up)
        else:
            vertex_normals = get_vert_normal(mesh, use_z_up)

        vertex_UVs     = get_vert_UVs(mesh)
        vertex_colors  = get_vert_color(mesh)
        vertex_groups  = get_vert_group(edit_object, bone_list)
        attributes     = get_attributes(mesh)
        bounding       = get_bounding(mesh, scale)
        
        bpy.data.objects.remove(edit_object) # remove edit mesh

        sector_count = 0
        sectors_list = [mesh_indices, vertex_coords, vertex_normals, vertex_UVs, vertex_colors, vertex_groups, attributes, bounding]
        for i, sector in enumerate(sectors_list):
            if len(sector) > 0:
                mesh_data_bytes.extend(sector)
                if sector is mesh_indices: sector_count += 3 # this bytearray has three sectors inside it: indices, used materials, material indices
                else: sector_count += 1
        
        insert_header(mesh_data_bytes, 0x00000004, sector_count) # mesh data container
        output_bytes.extend(mesh_data_bytes)
        
    
    insert_header(output_bytes, 0x00000002, mesh_count) # all models container
    output_bytes.extend(material_texture_bytes)
    if len(material_texture_bytes) > 0: total_sectors_in_file += 1
    
    # unknown, constant on all observed model files
    unk_data = bytearray(int32_write(0x10B0900))
    insert_header(unk_data, 0x00020000, 1)
    output_bytes[0:0] = unk_data # insert at start
    total_sectors_in_file += 1

    # main header
    insert_header(output_bytes, 0x1, total_sectors_in_file)

    return output_bytes, entry_info