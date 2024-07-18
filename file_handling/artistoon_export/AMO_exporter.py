import bpy
import math
import bmesh
import mathutils
from itertools import groupby
from ..binary_rw import int16_write, int32_write, float_write, int32_write_list, pad_bytes
from ..sector_handler import get_sector_size
from ...pyffi.utils import tristrip

def get_global_materials(collection):
    
    def get_mat_name(material):
        return material.name
    
    def get_tex_index(texture):
        return texture[3]
        
    matlist = []
    texlist = []
    
    out = []
    mat_sector = []
    tex_sector = []
    
    for obj in collection.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            for material in mesh.materials:
                if material not in matlist:
                    matlist.append(material)               
    matlist = sorted(matlist, key=get_mat_name)
    
    if len(collection.keys()) != 0:
        for x in range(len(collection.keys())):
            try:
                tex_property = collection[f'texture_{x}']
            except:
                continue
            texlist.append([tex_property[0], tex_property[1], tex_property[2], x])
    else:
        return

    texlist = sorted(texlist, key=get_tex_index)
    
    for x in range(len(matlist)):
        material = matlist[x]
        mat_type       = material['mat_type']
        mat_tex_image  = material['tex_image']
        mat_unk1       = material['unknown_1']
        mat_unk2       = material['unknown_2']
        mat_unk3       = material['unknown_3']
        mat_unk4_float = material['unknown_4']
        mat_unk5_int32 = material['unknown_5']
        
        mat_sector.append(int32_write(mat_type)) #head
        mat_sector.append(int32_write(1)) #count
        mat_sector.append(int32_write(0x110)) #size
        
        for unk in mat_unk1:
            mat_sector.append(float_write(unk))
        for unk in mat_unk2:
            mat_sector.append(float_write(unk))
        for unk in mat_unk3:
            mat_sector.append(float_write(unk))
#        mat_sector.append(float_write_list(mat_unk1))
#        mat_sector.append(float_write_list(mat_unk2))
#        mat_sector.append(float_write_list(mat_unk3))
        
        mat_sector.append(float_write(mat_unk4_float))
        mat_sector.append(int32_write(mat_unk5_int32))
        
        pad_bytes(mat_sector, 0x00, 0xC8)
        mat_sector.append(int32_write(mat_tex_image))
        
    mat_sector.insert(0, int32_write(0x00000009))
    mat_sector.insert(1, int32_write(len(matlist)))
    mat_sector.insert(2, get_sector_size(mat_sector))
    
    for x in mat_sector:
        out.append(x)
    
    for x in range(len(texlist)):
        tex_index  = texlist[x][0]
        tex_width  = texlist[x][1]
        tex_height = texlist[x][2]
        
        tex_sector.append(int32_write(0))
        tex_sector.append(int32_write(1))
        tex_sector.append(int32_write(0x10C))
        
        tex_sector.append(int32_write(tex_index))
        tex_sector.append(int32_write(tex_width))
        tex_sector.append(int32_write(tex_height))
        
        pad_bytes(tex_sector, 0x00, 0xF4)
    
    tex_sector.insert(0, int32_write(0x0000000A))
    tex_sector.insert(1, int32_write(len(texlist)))
    tex_sector.insert(2, get_sector_size(tex_sector))
    for x in tex_sector:
        out.append(x)
    return out

def get_indices(object, mesh, face_type):

    def write_indices(list, out):
        for poly in list:
            size = len(poly)
            out.append(int32_write(size))
            for vert in poly:
                out.append(int32_write(vert))

    def write_materials(facemats, matlist, out):
        for face_mat in facemats:
            for mat in mat_list:
                if face_mat == mat:
                    out.append(int32_write(mat_list.index(mat)))

    def add_face(split_faces, material_name, poly_verts):
        if material_name in split_faces:
            split_faces[material_name].append(poly_verts)
        else:
            split_faces[material_name] = [poly_verts]
    
    def collect_indices(faces, face_type):
        collected_indices = []
        collected_materials = []
        for material, indices in faces: #split_03_faces.items()
            print(indices)
            if face_type == 'TRI_STRIP': indices = tristrip.stripify(indices)
            for index in indices:
                collected_indices.append(index)
                collected_materials.append(material)
        return collected_indices, collected_materials
        
    
    out_bytes = []
    complex_verts = []
    mat_list = []

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
        
        # add materials to mat list
        material_name = mesh.materials[poly.material_index].name
        if material_name not in mat_list:
            mat_list.append(material_name)
        
        # add faces
        if any(vert in complex_verts for vert in poly_verts): # checking if there's any 04 type verts
            add_face(split_04_faces, material_name, poly_verts)
        else:
            add_face(split_03_faces, material_name, poly_verts)    
    
    print(f"Face Mode: {face_type}")
    indices_03, materials_03 = collect_indices(split_03_faces.items(), face_type) 
    indices_04, materials_04 = collect_indices(split_04_faces.items(), face_type) 

    # add strips to binary
    write_indices(indices_03, out_bytes)
    out_bytes.insert(0, int32_write(0x00030000)) # magic
    out_bytes.insert(1, int32_write(len(indices_03))) # count
    out_bytes.insert(2, get_sector_size(out_bytes)) # size
    if len(indices_04) != 0:
        out04 = []
        write_indices(indices_04, out04)
        out04.insert(0, int32_write(0x00040000)) # magic 
        out04.insert(1, int32_write(len(indices_04))) # count
        out04.insert(2, get_sector_size(out04)) # size
        for l in out04:
            out_bytes.append(l)
    
    #strip container
    out_bytes.insert(0, int32_write(0x00000005)) # magic 
    if len(indices_04) != 0: out_bytes.insert(1, int32_write(2)) # count = 2 if 04 strips exist (there's two strip sectors)
    else: out_bytes.insert(1, int32_write(1)) # count = 1 if only 03 strips exist
    out_bytes.insert(2, get_sector_size(out_bytes)) # size
    
    total_strips = len(indices_03) + len(indices_04)
    
    #material list container
    mat_count = len(mat_list)
    out_bytes.append(int32_write(0x00050000))
    out_bytes.append(int32_write(mat_count))
    out_bytes.append(int32_write(0xC+mat_count*4))
    for mat in mat_list: 
        mat_index = int(mat.split('_')[-1].split('.')[0][3:]) # gross
        out_bytes.append(int32_write(mat_index))
    
    #material per strip
    out_bytes.append(int32_write(0x00060000)) # magic
    out_bytes.append(int32_write(total_strips)) # count
    out_bytes.append(int32_write(0xC+total_strips*4)) # size 
    write_materials(materials_03, mat_list, out_bytes)
    write_materials(materials_04, mat_list, out_bytes)
    
    return out_bytes
  
def get_vert_coord(mesh, scale, z_up):
    out = []
    vert_count = int32_write(len(mesh.vertices))
    rotation = mathutils.Euler((math.radians(-90.0), 0.0, 0.0), 'XYZ')
    
    for vert in mesh.vertices:
        vertex_coord = mathutils.Vector([vert.co.xyz[0], vert.co.xyz[1], vert.co.xyz[2]])
        if z_up: vertex_coord.rotate(rotation)
        for coord in vertex_coord:
            out.append(float_write(coord*scale))
    
    out.insert(0, int32_write(0x00070000))
    out.insert(1, vert_count)
    out.insert(2, get_sector_size(out))
    #out.append(x for x in out)
    return out 

def get_vert_normal(mesh, z_up):
    out = []
    vert_count = int32_write(len(mesh.vertices))
    rotation = mathutils.Euler((math.radians(-90.0), 0.0, 0.0), 'XYZ')
    
    for vert in mesh.vertices:
        vertex_normal = mathutils.Vector((vert.normal[0], vert.normal[1], vert.normal[2]))
        if z_up: vertex_normal.rotate(rotation)
        for normal in vertex_normal:
            out.append(float_write(normal))
    
    out.insert(0, int32_write(0x00080000))
    out.insert(1, vert_count)
    out.insert(2, get_sector_size(out))
    #out.append(x for x in out)
    return out 

def get_vert_UVs(mesh): # GROSS ! ! !
    out = []
    vert_count = int32_write(len(mesh.vertices))
    
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
                out.append(float_write(uv[1][0]))
                out.append(float_write(1.0 - uv[1][1]))
                added_verts.append(vert_index)
                
    out.insert(0, int32_write(0x000A0000))
    out.insert(1, vert_count)
    out.insert(2, get_sector_size(out))
    #out.append(x for x in out)
    return out 

def get_vert_color(mesh):
    out = []
    vert_count = int32_write(len(mesh.vertices))
    color_attribute = mesh.color_attributes.active_color
    if color_attribute != None:
        for c in color_attribute.data:
            R = c.color[0] * 255
            G = c.color[1] * 255
            B = c.color[2] * 255
            A = c.color[3] * 255
            out.append(float_write(R))
            out.append(float_write(G))
            out.append(float_write(B))
            out.append(float_write(A))
    out.insert(0, int32_write(0x000B0000))
    out.insert(1, vert_count)
    out.insert(2, get_sector_size(out))
    #out.append(x for x in out)
    return out

def get_vert_group(object):
    out = []
    mesh = object.data
    vert_count = int32_write(len(mesh.vertices))
    if len(object.vertex_groups) > 0:
        for vert in mesh.vertices:
            vert_group = []
            for group in vert.groups:
                group_name = object.vertex_groups[group.group].name
                group_weight = group.weight
                vert_group.append([group_name, group_weight])
            out.append(int32_write(len(vert_group)))
            for x in vert_group:
                out.append(int32_write(int(x[0])))
                out.append(float_write(x[1]*100))
        out.insert(0, int32_write(0x000C0000))
        out.insert(1, vert_count)
        out.insert(2, get_sector_size(out))
        #out.append(x for x in out)
    return out

def get_attributes(mesh):
    out = []
    if len(mesh.keys()) != 0:
        attributes = [
            mesh.get('aa_render_dist'),
            mesh.get('aa_material'),
            mesh.get('aa_unknown_0x02'),
            mesh.get('aa_cull'),
            mesh.get('aa_scissor'),
            mesh.get('aa_light'),
            mesh.get('aa_unknown_0x06'),
            mesh.get('aa_uvscroll'),
            mesh.get('aa_unknown_0x08'),
            mesh.get('aa_fadecolor'),
            mesh.get('aa_special'),
            mesh.get('aa_unknown_0x0B'),
            mesh.get('aa_unknown_0x0C'),
            mesh.get('aa_unknown_0x0D'),
            mesh.get('aa_unknown_0x0E'),
            mesh.get('aa_unknown_0x0F'),
            mesh.get('aa_unknown_0x10'),
            mesh.get('aa_unknown_0x11')
            ]
        if None in attributes:
            return ""
        else:
            for x in int32_write_list(attributes):
                out.append(x)
            out.insert(0, int32_write(0x000F0000))
            out.insert(1, int32_write(1))
            out.insert(2, get_sector_size(out))
            #out.append(x for x in out)
            return out
    else:
        return

def get_bounding(mesh):
    out = []
    if len(mesh.keys()) != 0:
        bound = []
        for x in mesh.keys():
            if x.split('_')[0] == 'bounding':
                bound.append(x)
        if len(bound) != 0:
            for x in range(len(bound)):
                unk1 = list(mesh.get(f'bounding_{x}_unk1'))
                cull_range = list(mesh.get(f'culling_range'))
                for short in unk1:
                    out.append(int16_write(short))   
                for float in cull_range:
                    out.append(float_write(float))
            out.insert(0, int32_write(0x00110000)) 
            out.insert(1, int32_write(len(bound)))
            out.insert(2, get_sector_size(out))
        return out
    else:
        return

def triangulate_bmesh(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='LONG_EDGE')
    bm.to_mesh(mesh)
    bm.free()

def uv_split_bmesh(mesh): # GROSS !! ! ! !! 
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

def get_amo(uv_split, face_type, scale, z_up):
    finalbytes = []
    collection = bpy.context.view_layer.active_layer_collection.collection
    mesh_count = len([obj for obj in collection.objects if obj.type == 'MESH'])
    material_data = get_global_materials(collection)
    mesh_out = []
    
    for object in collection.objects:
        if object.type == 'MESH':
            out = []
            
            edit_object = object.copy()
            edit_object.data = object.data.copy()
            edit_object.data.calc_loop_triangles()
            mesh = edit_object.data
            
            triangulate_bmesh(mesh)
            if uv_split: uv_split_bmesh(mesh)
            
            mesh_indices   = get_indices(edit_object, mesh, face_type)
            vertex_coords  = get_vert_coord(mesh, scale, z_up)
            vertex_normals = get_vert_normal(mesh, z_up)
            vertex_UVs     = get_vert_UVs(mesh)
            vertex_colors  = get_vert_color(mesh)
            vertex_groups  = get_vert_group(edit_object)
            attributes     = get_attributes(mesh)
            bounding       = get_bounding(mesh)
            
            bpy.data.objects.remove(edit_object)
            
            sector_count = 0
            if len(mesh_indices) != 0:
                sector_count += 3
                for byte in mesh_indices:
                    out.append(byte)
                
            if len(vertex_coords) != 0:
                for byte in vertex_coords:
                    out.append(byte)
                sector_count += 1
            if len(vertex_normals) != 0:
                for byte in vertex_normals:
                    out.append(byte)
                sector_count += 1
            if len(vertex_UVs) != 0:
                for byte in vertex_UVs:
                    out.append(byte)
                sector_count += 1
            if len(vertex_colors) != 0:
                for byte in vertex_colors:
                    out.append(byte)
                sector_count += 1
            if len(vertex_groups) != 0:
                for byte in vertex_groups:
                    out.append(byte)
                sector_count += 1
            if len(attributes) != 0:
                for byte in attributes:
                    out.append(byte)
                sector_count += 1
            if len(bounding) != 0:
                for byte in bounding:
                    out.append(byte)
                sector_count += 1
            
            out.insert(0, int32_write(0x00000004))
            out.insert(1, int32_write(sector_count))
            out.insert(2, get_sector_size(out))
            for byte in out:
                mesh_out.append(byte)
    
    mesh_out.insert(0, int32_write(0x00000002))
    mesh_out.insert(1, int32_write(mesh_count))
    mesh_out.insert(2, get_sector_size(mesh_out))
    
    for byte in material_data:
        mesh_out.append(byte)
    
    mesh_out.insert(0, int32_write(0x00020000)) 
    mesh_out.insert(1, int32_write(1))
    mesh_out.insert(2, int32_write(0x10))
    mesh_out.insert(3, int32_write(0x10B0900)) #unknown
    
    mesh_out.insert(0, int32_write(0x00000001))
    mesh_out.insert(1, int32_write(0x00000004))
    mesh_out.insert(2, get_sector_size(mesh_out))
        
    return mesh_out

def write(context, filepath, uv_split, face_type, scale, z_up):
    print("Exporting Artistoon Model...")
    amo = get_amo(uv_split, face_type, scale, z_up)
    f = open(filepath, 'wb')
    for byte in amo:
        f.write(byte)
    f.close()
    return {'FINISHED'}

def all_equal(iterable):
    g = groupby(iterable)
    return next(g, True) and not next(g, False)