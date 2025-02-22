import bpy
import math
import bmesh
import mathutils
from itertools import groupby
from ..binary_rw import int08_write, int32_write, float_write, int32_write_list, pad_bytes
from ..sector_handler import get_sector_size
from ...pyffi.utils import tristrip

z_up_rotation = mathutils.Euler((math.radians(-90.0), 0.0, 0.0), 'XYZ')

def get_all_materials(collection):
    
    def get_material_name(material):
        return material.name.split('.')[0] # split so duplicate materials are indexed correctly
    
    def get_texture_properties(material):
        return {
        "AMO_TextureIndex" : material.AMO_TextureIndex,
        "AMO_TextureWidth" : material.AMO_TextureWidth,
        "AMO_TextureHeight" : material.AMO_TextureHeight }
    
    output_bytes = []
    material_list_sector_bytes = []
    texture_list_sector_bytes = []
    
    material_name_list = [] # for mesh indices
    material_list = [] # sorted list of materials from all meshes in the collections
    texture_list = [] # texture list generated of textures listed by material properties
    
    print(material_name_list)
    # collect all materials in the collections
    for obj in collection.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            for material in mesh.materials:
                if material not in material_list:
                    # add material's listed texture to texture list
                    texture_property = get_texture_properties(material)
                    if texture_property not in texture_list:
                        texture_list.append(get_texture_properties(material))
                    # setting the material's texture index to be the index of the texture in the texture list
                    material.AMO_TextureIndex = texture_list.index(texture_property)
                    material_list.append(material)
    print(". material_list={material_list}")
    material_list = sorted(material_list, key=get_material_name)
    
    # writing output bytes of material list 
    for material in material_list:
        material_name_list.append(material.name)

        material_list_sector_bytes.append(int32_write(material.AMO_MaterialType)) # head
        material_list_sector_bytes.append(int32_write(1)) # count
        material_list_sector_bytes.append(int32_write(0x110)) # size
        
        for float in material.AMO_ColorUnk1:
            material_list_sector_bytes.append(float_write(float))
        for float in material.AMO_ColorUnk2:
            material_list_sector_bytes.append(float_write(float))
        for float in material.AMO_ColorUnk3:
            material_list_sector_bytes.append(float_write(float))
        
        material_list_sector_bytes.append(float_write(material.AMO_Unknown4))
        material_list_sector_bytes.append(int32_write(material.AMO_Unknown5))
        pad_bytes(material_list_sector_bytes, 0x00, 0xC8)
        material_list_sector_bytes.append(int32_write(material.AMO_TextureIndex))
    
    # sector header
    material_list_sector_bytes.insert(0, int32_write(0x00000009)) # head
    material_list_sector_bytes.insert(1, int32_write(len(material_list))) # count
    material_list_sector_bytes.insert(2, get_sector_size(material_list_sector_bytes)) # size
    
    # writing output bytes of texture list 
    for texture in texture_list:
        texture_list_sector_bytes.append(int32_write(0)) # texture entry head
        texture_list_sector_bytes.append(int32_write(1)) # count
        texture_list_sector_bytes.append(int32_write(0x10C)) # size

        texture_list_sector_bytes.append(int32_write(texture["AMO_TextureIndex"]))
        texture_list_sector_bytes.append(int32_write(texture["AMO_TextureWidth"]))
        texture_list_sector_bytes.append(int32_write(texture["AMO_TextureHeight"]))
        pad_bytes(texture_list_sector_bytes, 0x00, 0xF4)
    
    # sector header
    texture_list_sector_bytes.insert(0, int32_write(0x0000000A)) # head
    texture_list_sector_bytes.insert(1, int32_write(len(texture_list))) # count
    texture_list_sector_bytes.insert(2, get_sector_size(texture_list_sector_bytes)) # size
    
    for byte in material_list_sector_bytes:
        output_bytes.append(byte)
    for byte in texture_list_sector_bytes:
        output_bytes.append(byte)
    return output_bytes, material_name_list


def get_indices(object, mesh, all_material_names, face_type):

    def write_indices(output_bytes, list):
        for poly in list:
            size = len(poly)
            output_bytes.append(int32_write(size))
            for vert in poly:
                output_bytes.append(int32_write(vert))

    def write_materials(face_material_index_list, mesh_material_list, output_bytes):
        for face_material in face_material_index_list:
            for material in mesh_material_list:
                if face_material == material:
                    output_bytes.append(int32_write(mesh_material_list.index(material)))

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
        
    
    output_bytes = []
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
    print(f"\n\n\nmaterialnamelist: {all_material_names}\n")
    for poly in mesh.polygons:
        poly_verts = list(poly.vertices)
        
        # add materials to material name list
        material_name = mesh.materials[poly.material_index].name
        print(f"{material_name}, ", end = '')
        if material_name not in mesh_material_list:
            print(f"\n - UNIQUE material_name: {material_name}")
            mesh_material_list.append(material_name)
        
        # add faces
        if any(vert in complex_verts for vert in poly_verts): # checking if there's any 04 type verts
            add_face(split_04_faces, material_name, poly_verts)
        else:
            add_face(split_03_faces, material_name, poly_verts)    
    
    print(f"Face Mode: {face_type}")
    indices_03, materials_03 = collect_indices(split_03_faces.items(), face_type) 
    indices_04, materials_04 = collect_indices(split_04_faces.items(), face_type) 

    # add strips to binary
    write_indices(output_bytes, indices_03)
    output_bytes.insert(0, int32_write(0x00030000)) # head
    output_bytes.insert(1, int32_write(len(indices_03))) # count
    output_bytes.insert(2, get_sector_size(output_bytes)) # size
    if len(indices_04) != 0:
        strip04_bytes = []
        write_indices(strip04_bytes, indices_04)
        strip04_bytes.insert(0, int32_write(0x00040000)) # head 
        strip04_bytes.insert(1, int32_write(len(indices_04))) # count
        strip04_bytes.insert(2, get_sector_size(strip04_bytes)) # size
        for l in strip04_bytes:
            output_bytes.append(l)
    
    # strip container
    output_bytes.insert(0, int32_write(0x00000005)) # head 
    if len(indices_04) != 0: output_bytes.insert(1, int32_write(2)) # count = 2 if 04 strips exist (mean there's two strip sectors)
    else: output_bytes.insert(1, int32_write(1)) # count = 1 if only 03 strips exist
    output_bytes.insert(2, get_sector_size(output_bytes)) # size of all strips thus far
    
    total_strip_count = len(indices_03) + len(indices_04)
    
    # mesh material list 
    material_count = len(mesh_material_list)
    output_bytes.append(int32_write(0x00050000))
    output_bytes.append(int32_write(material_count))
    output_bytes.append(int32_write(0xC+material_count*4))
    for material in mesh_material_list: 
        material_index = all_material_names.index(material)
        output_bytes.append(int32_write(material_index))
    
    # material per strip
    output_bytes.append(int32_write(0x00060000)) # head
    output_bytes.append(int32_write(total_strip_count)) # count
    output_bytes.append(int32_write(0xC+total_strip_count*4)) # size 
    write_materials(materials_03, mesh_material_list, output_bytes)
    write_materials(materials_04, mesh_material_list, output_bytes)
    
    return output_bytes


def get_vert_coord(mesh, scale, use_z_up):
    output_bytes = []
    vertex_count = int32_write(len(mesh.vertices))

    for vert in mesh.vertices:
        vertex_coord = mathutils.Vector([vert.co.xyz[0], vert.co.xyz[1], vert.co.xyz[2]])
        if use_z_up: vertex_coord.rotate(z_up_rotation)
        for coord in vertex_coord:
            output_bytes.append(float_write(coord*scale))
    
    output_bytes.insert(0, int32_write(0x00070000)) # head
    output_bytes.insert(1, vertex_count) # count
    output_bytes.insert(2, get_sector_size(output_bytes)) # size
    return output_bytes 


def get_vert_normal(mesh, use_z_up):
    output_bytes = []
    vertex_count = int32_write(len(mesh.vertices))
    
    for vert in mesh.vertices:
        vertex_normal = mathutils.Vector((vert.normal[0], vert.normal[1], vert.normal[2]))
        if use_z_up: vertex_normal.rotate(z_up_rotation)
        for normal in vertex_normal:
            output_bytes.append(float_write(normal))
    
    output_bytes.insert(0, int32_write(0x00080000)) # head
    output_bytes.insert(1, vertex_count) # count
    output_bytes.insert(2, get_sector_size(output_bytes)) # size
    return output_bytes 


def get_loop_normal(mesh, use_z_up):
    output_bytes = []
    vertex_count = int32_write(len(mesh.vertices))
    
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
        if use_z_up: normal.rotate(z_up_rotation)
        for direction in normal:
            output_bytes.append(float_write(direction))
    
    output_bytes.insert(0, int32_write(0x00080000)) # head
    output_bytes.insert(1, vertex_count) # count
    output_bytes.insert(2, get_sector_size(output_bytes)) # size
    return output_bytes 


def get_vert_UVs(mesh): # todo: GROSS ! ! !
    output_bytes = []
    vertex_count = int32_write(len(mesh.vertices))
    
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
                output_bytes.append(float_write(uv[1][0]))
                output_bytes.append(float_write(1.0 - uv[1][1]))
                added_verts.append(vert_index)
                
    output_bytes.insert(0, int32_write(0x000A0000)) # head
    output_bytes.insert(1, vertex_count) # count
    output_bytes.insert(2, get_sector_size(output_bytes)) # size
    return output_bytes 


def get_vert_color(mesh):
    output_bytes = []
    vertex_count = int32_write(len(mesh.vertices))
    color_attribute = mesh.color_attributes.active_color
    
    if color_attribute != None:
        for vertex_color in color_attribute.data:
            red   = vertex_color.color[0] * 255
            green = vertex_color.color[1] * 255
            blue  = vertex_color.color[2] * 255
            alpha = vertex_color.color[3] * 255
            output_bytes.append(float_write(red))
            output_bytes.append(float_write(green))
            output_bytes.append(float_write(blue))
            output_bytes.append(float_write(alpha))
    
    output_bytes.insert(0, int32_write(0x000B0000)) # head
    output_bytes.insert(1, vertex_count) # count
    output_bytes.insert(2, get_sector_size(output_bytes)) # size
    return output_bytes


def get_vert_group(object):
    output_bytes = []
    mesh = object.data
    vertex_count = int32_write(len(mesh.vertices))
    
    if len(object.vertex_groups) > 0:
        
        for vert in mesh.vertices:
            vertex_group_data = []
            for group in vert.groups:
                group_name = object.vertex_groups[group.group].name 
                group_weight = group.weight * 100 # model format weights are in the range 0 - 100
                vertex_group_data.append({
                    "name" : int(group_name), # todo: relying on bone name being an int is GROSS.
                    "weight" : group_weight
                    })
            
            output_bytes.append(int32_write(len(vertex_group_data))) # count of how many groups influence the current vertex
            for group in vertex_group_data:
                output_bytes.append(int32_write(group["name"]))
                output_bytes.append(float_write(group["weight"]))
        
        output_bytes.insert(0, int32_write(0x000C0000)) # head
        output_bytes.insert(1, vertex_count) # count
        output_bytes.insert(2, get_sector_size(output_bytes))# size
    return output_bytes


def get_attributes(mesh):
    output_bytes = []

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

    for byte in int32_write_list(attributes):
        output_bytes.append(byte)
    
    output_bytes.insert(0, int32_write(0x000F0000)) # head
    output_bytes.insert(1, int32_write(1)) # count
    output_bytes.insert(2, get_sector_size(output_bytes)) # size
    return output_bytes


def get_bounding(mesh, scale):
    if mesh.AMO_HasBounding == False: return ()
    
    output_bytes = []
    
    for float in mesh.AMO_Bounding:
        output_bytes.append(float_write(float*scale))
    output_bytes.insert(0, int32_write(0x00110000)) # size
    output_bytes.insert(1, int32_write(1)) # count
    output_bytes.insert(2, get_sector_size(output_bytes)) # head

    return output_bytes


def triangulate_bmesh(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='LONG_EDGE')
    bm.to_mesh(mesh)
    bm.free()


def uv_split_bmesh(mesh): # todo: GROSS !! ! ! !! 
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


def get_amo(collection, uv_split, face_type, normal_type, scale, use_z_up):
    output_bytes = []
    material_texture_bytes, all_material_names = get_all_materials(collection)
    mesh_count = len([obj for obj in collection.objects if obj.type == 'MESH'])
    
    for object in collection.objects:
        if object.type == 'MESH':
            mesh_data_bytes = []
            
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
            
            mesh_indices   = get_indices(edit_object, mesh, all_material_names, face_type)
            vertex_coords  = get_vert_coord(mesh, scale, use_z_up)
            
            if normal_type == 'LOOP_NORMALS':
                vertex_normals = get_loop_normal(mesh, use_z_up)
            else:
                vertex_normals = get_vert_normal(mesh, use_z_up)
            
            vertex_UVs     = get_vert_UVs(mesh)
            vertex_colors  = get_vert_color(mesh)
            vertex_groups  = get_vert_group(edit_object)
            attributes     = get_attributes(mesh)
            bounding       = get_bounding(mesh, scale)
            
            bpy.data.objects.remove(edit_object) # remove edit mesh
            
            sector_count = 0
            if len(mesh_indices) != 0:
                sector_count += 3
                for byte in mesh_indices:
                    mesh_data_bytes.append(byte)

            if len(vertex_coords) != 0:
                for byte in vertex_coords:
                    mesh_data_bytes.append(byte)
                sector_count += 1
            
            if len(vertex_normals) != 0:
                for byte in vertex_normals:
                    mesh_data_bytes.append(byte)
                sector_count += 1
            
            if len(vertex_UVs) != 0:
                for byte in vertex_UVs:
                    mesh_data_bytes.append(byte)
                sector_count += 1
            
            if len(vertex_colors) != 0:
                for byte in vertex_colors:
                    mesh_data_bytes.append(byte)
                sector_count += 1
            
            if len(vertex_groups) != 0:
                for byte in vertex_groups:
                    mesh_data_bytes.append(byte)
                sector_count += 1
            
            if len(attributes) != 0:
                for byte in attributes:
                    mesh_data_bytes.append(byte)
                sector_count += 1
            
            if len(bounding) != 0:
                for byte in bounding:
                    mesh_data_bytes.append(byte)
                sector_count += 1
            
            mesh_data_bytes.insert(0, int32_write(0x00000004)) # model: mesh data container
            mesh_data_bytes.insert(1, int32_write(sector_count))
            mesh_data_bytes.insert(2, get_sector_size(mesh_data_bytes))
            for byte in mesh_data_bytes:
                output_bytes.append(byte)
    
    output_bytes.insert(0, int32_write(0x00000002)) # model container
    output_bytes.insert(1, int32_write(mesh_count))
    output_bytes.insert(2, get_sector_size(output_bytes))
    
    for byte in material_texture_bytes:
        output_bytes.append(byte)
    
    output_bytes.insert(0, int32_write(0x00020000)) 
    output_bytes.insert(1, int32_write(1))
    output_bytes.insert(2, int32_write(0x10))
    output_bytes.insert(3, int32_write(0x10B0900)) #unknown
    
    output_bytes.insert(0, int32_write(0x00000001))
    output_bytes.insert(1, int32_write(0x00000004))
    output_bytes.insert(2, get_sector_size(output_bytes))
        
    return output_bytes


def write(context, filepath, uv_split, face_type, normal_type, scale, use_z_up):
    print("Exporting Artistoon Model...")
    collection = bpy.context.view_layer.active_layer_collection.collection
    amo_bytes = get_amo(collection, uv_split, face_type, normal_type, scale, use_z_up)
    output_file = open(filepath, 'wb')
    for byte in amo_bytes:
        output_file.write(byte)
    output_file.close()
    return {'FINISHED'}


def all_equal(iterable):
    g = groupby(iterable)
    return next(g, True) and not next(g, False)