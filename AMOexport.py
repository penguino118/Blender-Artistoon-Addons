import bpy
import struct

bl_info = {
    "name": "Artistoon Model Exporter",
    "description": "Exporter for the Artistoon Model Format (AMO) found in GioGio's Bizarre Adventure.",
    "author": "Penguino",
    "version": (2, 1),
    "blender": (3, 6, 1),
    "location": "File > Export",
    "warning": "", # used for warning icon and text in addons panel
    "category": "Export",
}

def int16_write(int):
    return struct.pack('<H', int)

def int32_write(int):
    return struct.pack('<I', int)

def float_write(float):
    return struct.pack('<f', float)
    
def int32_write_list(list):
    tmpb = []
    for x in list:
        tmpb.append(struct.pack('<I', x))
    return tmpb

def get_sector_size(array):
    tmpb = 0x4
    for fun in array:
        ppp = fun.hex()
        tmpb += int(len(ppp)/2)
    tmpb = int32_write(tmpb)
    return tmpb
    
def pad_bytes(input_list, input_byte, size):
    l = [input_byte] * (size//4)
    #pad = []
    for v in l:
        input_list.append(int32_write(v))
    #return pad


def get_global_materials(collection):
    
    def get_name(material):
        return material.name

    def get_index(texture):
        return texture[0]
    
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
    matlist = sorted(matlist, key=get_name)
    
    if len(collection.keys()) != 0:
        for x in range(len(collection.keys())):
            try:
                tex_property = collection[f'texture_{x}']
            except:
                continue
            texlist.append([tex_property[0], tex_property[1], tex_property[2]])
    else:
        return
    print(texlist)
    texlist = sorted(texlist, key=get_index)
    
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

def get_indices(object, optimize_attempt):
    
    out = []
    mesh = object.data
    
    def add_indices(list, out):
        for poly in list:
            size = len(poly)
            out.append(int32_write(size))
            for vert in poly:
                out.append(int32_write(vert))
            #out.insert(0, int32_write(size))
    
    def add_materials(facemats, matlist, out):
        for face_mat in facemats:
            for mat in mat_list:
                if face_mat == mat:
                    out.append(int32_write(mat_list.index(mat)))
    
    def add_face(poly_verts, index_list, material_list):
        if len(poly_verts) == 4: #quads
            poly_verts = [poly_verts[2], poly_verts[3], poly_verts[1], poly_verts[0]]
        index_list.append(poly_verts)
        material_list.append(mat)
    
    complex_verts = []
    indices_03 = []
    indices_04 = []
    mat_list = []
    
    
    for vert in mesh.vertices: #gather indices for type 04 list
        vert_group = []
        for groupss in vert.groups:
            group_name = object.vertex_groups[groupss.group].name
            group_weight = groupss.weight
            vert_group.append([group_name, group_weight])
        if len(vert_group) > 1:
            complex_verts.append(vert.index)

    materials_03 = []
    materials_04 = []
    
    for poly in mesh.polygons:
        #for vert in poly.vertices:
        poly_verts = list(poly.vertices)
        mat = mesh.materials[poly.material_index].name
        if mat not in mat_list:
                mat_list.append(mat)
        
        if any(vert in complex_verts for vert in poly_verts):
            add_face(poly_verts, indices_04, materials_04)
        else:
            add_face(poly_verts, indices_03, materials_03)
    
    if optimize_attempt:
        stripped = stripify(indices_03, materials_03, 2500)
        indices_03 = stripped[0]
        materials_03 = stripped[1]
        if len(indices_04) != 0:
            stripped = stripify(indices_04, materials_04, 2500)
            indices_04 = stripped[0]
            materials_04 = stripped[1]
    
    #strips
    add_indices(indices_03, out)
    out.insert(0, int32_write(0x00030000))
    out.insert(1, int32_write(len(indices_03)))
    out.insert(2, get_sector_size(out))
    if len(indices_04) != 0:
        out04 = []
        add_indices(indices_04, out04)
        out04.insert(0, int32_write(0x00040000))
        out04.insert(1, int32_write(len(indices_04)))
        out04.insert(2, get_sector_size(out04))
        for l in out04:
            out.append(l)
    
    #strip container
    out.insert(0, int32_write(0x00000005))
    if len(indices_04) != 0: out.insert(1, int32_write(2))
    else: out.insert(1, int32_write(1))
    out.insert(2, get_sector_size(out))
    
    total_strips = len(indices_03) + len(indices_04)
    
    #material list container
    mat_count = len(mat_list)
    out.append(int32_write(0x00050000))
    out.append(int32_write(mat_count))
    out.append(int32_write(0xC+mat_count*4))
    for mat in mat_list: 
        mat_index = int(mat.split('_')[-1].split('.')[0][3:]) #gross
        out.append(int32_write(mat_index))
    
    #material per strip
    out.append(int32_write(0x00060000))
    out.append(int32_write(total_strips)) #mat count
    out.append(int32_write(0xC+total_strips*4)) #mat size 
    add_materials(materials_03, mat_list, out)
    add_materials(materials_04, mat_list, out)
    
    return out

#def stripify(ogtris, ogmats, pass_count, new_tris, new_mats):
def stripify(tri_list, mat_list, pass_count):
    #tri_list = ogtris
    #mat_list = ogmats
    
    new_tris = []
    new_mats = []
    
    removecount = 0
    
    for passindex in range(pass_count):
        for index in range(len(tri_list)-1):
            
            sizecheck = len(tri_list)-1-removecount
            if index < sizecheck:
                triscompared = compare_tris(tri_list[index], tri_list[index+1], mat_list[index], mat_list[index+1]) 
                
                if triscompared == 1:
                    build_strip(tri_list[index], tri_list[index+1], index, tri_list, mat_list, new_tris, new_mats, 1)
                    removecount = removecount+1
                
                elif triscompared == 2:
                    build_strip(tri_list[index], tri_list[index+1], index, tri_list, mat_list, new_tris, new_mats, 2)
                    removecount = removecount+1
                
                elif triscompared == 3:
                    build_strip(tri_list[index], tri_list[index+1], index, tri_list, mat_list, new_tris, new_mats, 3)
                    removecount = removecount+1
                
    print(f"Adding remaining triangles ({len(tri_list)})...")
    for x in tri_list:
        new_tris.append(x)
    print(f"Adding remaining materials ({len(mat_list)})...")
    for x in mat_list:
        new_mats.append(x)
    return [new_tris, new_mats]
    
def compare_tris(tris_A, tris_B, mat_A, mat_B):
    if tris_A[-3] == tris_B[-3] and tris_A[-1] == tris_B[-2] and mat_A == mat_B: #strip right
        return 1
    elif tris_A[-2] == tris_B[-3] and tris_A[-1] == tris_B[-1] and mat_A == mat_B: #strip down 
        return 2
    elif tris_A[-3] == tris_B[-3] and tris_A[-1] == tris_B[-2] and mat_A == mat_B: #strip up
        return 3
    
def build_strip(tris_A, tris_B, remainder, tri_list, mat_list, new_tris, new_mats, order):
    if order == 1: #right
        stripped_tris = [ tris_A[-2], tris_A[-1], tris_A[-3], tris_B[-1] ]
    elif order == 2: #down
        stripped_tris = [ tris_A[-3], tris_A[-2], tris_A[-1], tris_B[-2] ]
    elif order == 3: #up
        stripped_tris = [ tris_A[-2], tris_A[-1], tris_A[-3], tris_B[-1] ]
    new_tris.append(stripped_tris)
    new_mats.append(mat_list[remainder])
    tri_list.pop(remainder)
    tri_list.pop(remainder)
    mat_list.pop(remainder)
    mat_list.pop(remainder)
  
def get_vert_coord(object):
    out = []
    mesh = object.data
    vert_count = int32_write(len(mesh.vertices))
    
    for vert in mesh.vertices:
        #coord = [vert.co.xyz[0], vert.co.xyz[1], vert.co.xyz[2]]
        out.append(float_write(vert.co.xyz[0]))
        out.append(float_write(vert.co.xyz[1]))
        out.append(float_write(vert.co.xyz[2]))
        #out.append(x for x in float_write_list(coord))
    
    out.insert(0, int32_write(0x00070000))
    out.insert(1, vert_count)
    out.insert(2, get_sector_size(out))
    #out.append(x for x in out)
    return out 

def get_vert_normal(object):
    out = []
    mesh = object.data
    vert_count = int32_write(len(mesh.vertices))
    
    for vert in mesh.vertices:
        #vnorm = vert.
        out.append(float_write(vert.normal[0]))
        out.append(float_write(vert.normal[1]))
        out.append(float_write(vert.normal[2]))
        #out.append(x for x in float_write_list(vnorm))
    
    out.insert(0, int32_write(0x00080000))
    out.insert(1, vert_count)
    out.insert(2, get_sector_size(out))
    #out.append(x for x in out)
    return out 

def get_vert_UVs(object):
    out = []
    mesh = object.data
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

def get_vert_color(object):
    out = []
    mesh = object.data
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

def get_attributes(object):
    mesh = object.data
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

def get_bounding(object):
    mesh = object.data
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

def get_amo(optimize):
    finalbytes = []
    collection = bpy.context.view_layer.active_layer_collection.collection
    mesh_count = len([obj for obj in collection.objects if obj.type == 'MESH'])
    material_data = get_global_materials(collection)
    mesh_out = []
    
    for object in collection.objects:
        if object.type == 'MESH':
            out = []
            object.data.calc_loop_triangles()
            object.data.calc_normals_split()
            
            mesh_indices   = get_indices(object, optimize)
            vertex_coords  = get_vert_coord(object)
            vertex_normals = get_vert_normal(object)
            vertex_UVs     = get_vert_UVs(object)
            vertex_colors  = get_vert_color(object)
            vertex_groups  = get_vert_group(object)
            attributes     = get_attributes(object)
            bounding       = get_bounding(object)
            
            object.data.free_normals_split()
            
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


def write_some_data(context, filepath, optimize_attempt):
    print("running write_some_data...")
    amo = get_amo(optimize_attempt)
    f = open(filepath, 'wb')
    for byte in amo:
        #print(byte.hex())
        f.write(byte)
    f.close()

    return {'FINISHED'}

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class Export_AMO(Operator, ExportHelper):
    """Export selected collection as Artistoon Model data."""
    bl_idname = "export_scene.amo"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Artistoon Model"

    # ExportHelper mixin class uses this
    filename_ext = ".amo"

    filter_glob: StringProperty(
        default="*.amo",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    optimize_attempt: BoolProperty(
        name="Optimize Meshes",
        description="Attempts optimize meshes by joining neighbour triangles into triangle strips.",
        default=False,
    )

#    type: EnumProperty(
#        name="Example Enum",
#        description="Choose between two items",
#        items=(
#            ('OPT_A', "First Option", "Description one"),
#            ('OPT_B', "Second Option", "Description two"),
#        ),
#        default='OPT_A',
#    )

    def execute(self, context):
        return write_some_data(context, self.filepath, self.optimize_attempt)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(Export_AMO.bl_idname, text="Artistoon Model (.amo)")


# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
def register():
    bpy.utils.register_class(Export_AMO)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(Export_AMO)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_scene.amo('INVOKE_DEFAULT')
