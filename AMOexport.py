import bpy
import struct

bl_info = {
    "name": "Artistoon Model Exporter",
    "description": "Exporter for the Artistoon Model Format (AMO) found in GioGio's Bizarre Adventure.",
    "author": "Penguino",
    "version": (2, 0),
    "blender": (3, 6, 1),
    "location": "File > Export",
    "warning": "", # used for warning icon and text in addons panel
    "category": "Export",
}

def int32_write(int):
    tmpb = f"{struct.unpack('>I', struct.pack('<I', int))[0]:08X}"
    return tmpb

def float_write(float):
    tmpb = f"{struct.unpack('>I', struct.pack('<f', float))[0]:08X}"
    return tmpb
    
def int32_write_list(list):
    tmpb = ""
    for x in list:
        tmpb += f"{struct.unpack('>I', struct.pack('<I', x))[0]:08X} "
    return tmpb

def int16_write_list(list):
    tmpb = ""
    for x in list:
        tmpb += f"{struct.unpack('>H', struct.pack('<H', x))[0]:04X} "
    return tmpb

def float_write_list(list):
    tmpb = ""
    for x in list:
        tmpb += f"{struct.unpack('>I', struct.pack('<f', x))[0]:08X} "
    return tmpb

def get_sector_size(array):
    tmpb = len(bytes.fromhex(f"{int32_write(1)} {int32_write(1)} {int32_write(1)} {array}"))
    tmpb = int32_write(tmpb)
    return tmpb

def pad_bytes(size):
    l = [0] * (size//4)
    pad = ""
    for v in l:
        pad += (f"{int32_write(v)}")
    return pad

def get_name(object):
    return object.name

def get_global_materials(collection):
    matlist = []
    texlist = []
    
    out = ""
    mat_sector = ""
    tex_sector = ""
    
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
    
    for x in range(len(matlist)):
        material = matlist[x]
        mat_type       = material['mat_type']
        mat_tex_image  = material['tex_image']
        mat_unk1       = material['unknown_1']
        mat_unk2       = material['unknown_2']
        mat_unk3       = material['unknown_3']
        mat_unk4_float = material['unknown_4']
        mat_unk5_int32 = material['unknown_5']
        mat_sector += f"{int32_write(mat_type)} {int32_write(1)} {int32_write(0x110)} " #head
        mat_sector += f"{float_write_list(mat_unk1)} {float_write_list(mat_unk2)} {float_write_list(mat_unk3)} "
        mat_sector += f"{float_write(mat_unk4_float)} {int32_write(mat_unk5_int32)} "
        mat_sector += f"{pad_bytes(0xC8)} {int32_write(mat_tex_image)} "
        
    out += f"{int32_write(0x00000009)} {int32_write(len(matlist))} {get_sector_size(mat_sector)}"
    out += f"{mat_sector}"
    
    for x in range(len(texlist)):
        tex_index  = texlist[x][0]
        tex_width  = texlist[x][1]
        tex_height = texlist[x][2]
        
        tex_sector += f"{int32_write(0)} {int32_write(1)} {int32_write(0x10C)}"
        tex_sector += f"{int32_write(tex_index)} {int32_write(tex_width)} {int32_write(tex_height)}"
        tex_sector += f"{pad_bytes(0xF4)} "
    
    out += f"{int32_write(0x0000000A)} {int32_write(len(texlist))} {get_sector_size(tex_sector)}"
    out += f"{tex_sector}"
    return out

def get_indices(object, optimize_attempt):
    out = ""
    mesh = object.data
    
    indices_03 = []
    indices_04 = []
    mat_list = []
    #gather indices for type 04 list
    complex_verts = []
    for vert in mesh.vertices:
        vert_group = []
        for groupss in vert.groups:
            group_name = object.vertex_groups[groupss.group].name
            group_weight = groupss.weight
            vert_group.append([group_name, group_weight])
        if len(vert_group) > 1:
            complex_verts.append(vert.index)
    #faces
    strip03 = []
    strip04 = []
    mats03 = []
    mats04 = []

    for poly in mesh.polygons:
        #for vert in poly.vertices:
        poly_verts = list(poly.vertices)
        mat = mesh.materials[poly.material_index].name
        if mat not in mat_list:
                mat_list.append(mat)
        if any(vert in complex_verts for vert in poly_verts):
            if len(poly_verts) == 4: #quads
                poly_verts = [poly_verts[2], poly_verts[3], poly_verts[1], poly_verts[0]]
            strip04.append(poly_verts)
            mats04.append(mat)
        else:
            if len(poly_verts) == 4: #quads
                poly_verts = [poly_verts[2], poly_verts[3], poly_verts[1], poly_verts[0]]
            strip03.append(poly_verts)
            print(poly_verts)
            mats03.append(mat)
      
    indices_03 = []
    indices_04 = []
    mat_indices_03 = []
    mat_indices_04 = []
    
    if optimize_attempt == True:
        stripify(strip03, mats03, 4000, indices_03, mat_indices_03)
        if len(complex_verts) > 0:
            stripify(strip04, mats04, 4000, indices_04, mat_indices_04)
    else:
        indices_03 = strip03
        indices_04 = strip04
        mat_indices_03 = mats03
        mat_indices_04 = mats04
   
    #strip container
    out03 = ""
    out04 = ""

    for face in indices_03:
        out03 += f"{int32_write(len(face))} {int32_write_list(face)} "
    for face in indices_04:
        out04 += f"{int32_write(len(face))} {int32_write_list(face)} "
    
    if len(indices_04) == 0:
        strip_count = 1
        out03 = f"{int32_write(0x00030000)} {int32_write(len(indices_03))} {get_sector_size(out03)} {out03}"
        strip_out = f"{out03} "
    elif len(indices_03) == 0:
        strip_count = 1
        out04 = f"{int32_write(0x00040000)} {int32_write(len(indices_04))} {get_sector_size(out04)} {out04}"
        strip_out = f"{out04} "
    else:
        strip_count = 2
        out03 = f"{int32_write(0x00030000)} {int32_write(len(indices_03))} {get_sector_size(out03)} {out03}"
        out04 = f"{int32_write(0x00040000)} {int32_write(len(indices_04))} {get_sector_size(out04)} {out04}"
        strip_out = f"{out04} {out03} "
    strip_out = f"{int32_write(0x00000005)} {int32_write(strip_count)} {get_sector_size(strip_out)} {strip_out}"
    
    #material container
    mat_out = ""
    for mat in mat_list:
        mat_index = int(mat.split('_')[-1].split('.')[0][3:])
        mat_out += f"{int32_write(mat_index)}"
    mat_out = f"{int32_write(0x00050000)} {int32_write(len(mat_list))} {get_sector_size(mat_out)} {mat_out}"
    
    #material per strip
    fmat_out = ""
    fmat_03 = ""
    fmat_04 = ""
    
    for face_mat in mat_indices_03:
        for mat in mat_list:
            if face_mat == mat:
                fmat_03 += f"{int32_write(mat_list.index(mat))}"
    
    for face_mat in mat_indices_04:
        for mat in mat_list:
            if face_mat == mat:
                fmat_04 += f"{int32_write(mat_list.index(mat))}"
    
    fmat_out = f"{fmat_04} {fmat_03} " 
    facemat_count = len(indices_04) + len(indices_03)
    fmat_out = f"{int32_write(0x00060000)} {int32_write(facemat_count)} {get_sector_size(fmat_out)} {fmat_out}"
    out = f"{strip_out} {mat_out} {fmat_out}"
    return out

def stripify(ogtris, ogmats, pass_count, new_tris, new_mats):
    tri_list = ogtris
    mat_list = ogmats
    
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
                
                elif triscompared == 0:
                    tri_list.insert(len(tri_list)+1, tri_list[index])
                    mat_list.insert(len(mat_list)+1, mat_list[index])
                    tri_list.pop(index)
                    mat_list.pop(index)
                
    print(f"Adding remaining triangles ({len(tri_list)})...")
    for x in tri_list:
        new_tris.append(x)
    print(f"Adding remaining materials ({len(mat_list)})...")
    for x in mat_list:
        new_mats.append(x)
    
def compare_tris(tris_A, tris_B, mat_A, mat_B):
    if tris_A[-3] == tris_B[-3] and tris_A[-1] == tris_B[-2] and mat_A == mat_B: #strip right
        return 1
    elif tris_A[-2] == tris_B[-3] and tris_A[-1] == tris_B[-1] and mat_A == mat_B: #strip down 
        return 2
    elif tris_A[-3] == tris_B[-3] and tris_A[-1] == tris_B[-2] and mat_A == mat_B: #strip up
        return 3
    else:
        return 0
    
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
    out = ""
    mesh = object.data
    vert_count = int32_write(len(mesh.vertices))
    
    for vert in mesh.vertices:
        coord = [vert.co.xyz[0], vert.co.xyz[1], vert.co.xyz[2]]
        out += f"{float_write_list(coord)}"
    
    out = f"{int32_write(0x00070000)} {vert_count} {get_sector_size(out)} {out}"
    return out 

def get_vert_normal(object):
    out = ""
    mesh = object.data
    vert_count = int32_write(len(mesh.vertices))
    
    for vert in mesh.vertices:
        vnorm = vert.normal
        out += f"{float_write(vnorm[0])} {float_write(vnorm[1])} {float_write(vnorm[2])} "

    out = f"{int32_write(0x00080000)} {vert_count} {get_sector_size(out)} {out}"
    return out 

def get_vert_UVs(object):
    out = ""
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
                out += f"{float_write(uv[1][0])} {float_write(1.0 - uv[1][1])}"
                added_verts.append(vert_index)
    out = f"{int32_write(0x000A0000)} {vert_count} {get_sector_size(out)} {out}"
    return out 

def get_vert_color(object):
    out = ""
    mesh = object.data
    vert_count = int32_write(len(mesh.vertices))
    color_attribute = mesh.color_attributes.active_color
    if color_attribute != None:
        for c in color_attribute.data:
            R = c.color[0] * 255
            G = c.color[1] * 255
            B = c.color[2] * 255
            A = c.color[3] * 255
            out += f"{float_write(R)} {float_write(G)} {float_write(B)} {float_write(A)} "
    out = f"{int32_write(0x000B0000)} {vert_count} {get_sector_size(out)} {out}"
    return out

def get_vert_group(object):
    out = ""
    mesh = object.data
    vert_count = int32_write(len(mesh.vertices))
    if len(object.vertex_groups) > 0:
        for vert in mesh.vertices:
            vert_group = []
            for group in vert.groups:
                group_name = object.vertex_groups[group.group].name
                group_weight = group.weight
                vert_group.append([group_name, group_weight])
            out += f"{int32_write(len(vert_group))}"
            for x in vert_group:
                out += f"{int32_write(int(x[0]))} {float_write(x[1]*100)}"
        
        out = f"{int32_write(0x000C0000)} {vert_count} {get_sector_size(out)} {out}"
    return out

def get_attributes(object):
    mesh = object.data
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
            out = f"{int32_write_list(attributes)}"
            out = f"{int32_write(0x000F0000)} {int32_write(1)} {get_sector_size(out)} {out}"
            return out
    else:
        return

def get_bounding(object):
    mesh = object.data
    out = ""
    if len(mesh.keys()) != 0:
        bound = []
        for x in mesh.keys():
            if x.split('_')[0] == 'bounding':
                bound.append(x)
        if len(bound) != 0:
            for x in range(len(bound)//2):
                unk1 = list(mesh.get(f'bounding_{x}_unk1'))
                unk2 = list(mesh.get(f'bounding_{x}_unk2'))
                out += f"{int16_write_list(unk1)} {float_write_list(unk2)}"
            out = f"{int32_write(0x00110000)} {int32_write(len(bound)//2)} {get_sector_size(out)} {out}"
        return out
    else:
        return

def get_amo(optimize):
    finalbytes = ""
    collection = bpy.context.view_layer.active_layer_collection.collection
    mesh_count = len([obj for obj in collection.objects if obj.type == 'MESH'])
    material_data = get_global_materials(collection)
    mesh_out = ""
    
    for object in collection.objects:
        if object.type == 'MESH':
            
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
            if len(mesh_indices) != 0: sector_count += 3
            if len(vertex_coords) != 0: sector_count += 1
            if len(vertex_normals) != 0: sector_count += 1
            if len(vertex_UVs) != 0: sector_count += 1
            if len(vertex_colors) != 0: sector_count += 1
            if len(vertex_groups) != 0: sector_count += 1
            if len(attributes) != 0: sector_count += 1
            if len(bounding) != 0: sector_count += 1
              
            out = f"{mesh_indices} {vertex_coords} {vertex_normals} {vertex_UVs} "
            out += f"{vertex_colors} {vertex_groups} {attributes} {bounding} "
            mesh_out += f"{int32_write(0x00000004)} {int32_write(sector_count)} {get_sector_size(out)} {out}"

    model_index = f"{int32_write(0x00000002)} {int32_write(mesh_count)} {get_sector_size(mesh_out)} {mesh_out}"
    head_unknown = f"{int32_write(0x00020000)} {int32_write(1)} {int32_write(0x10)} {int32_write(0x10B0900)}"
    head = f"{head_unknown} {model_index} {material_data}"
    out_bytes = f"{int32_write(0x00000001)} {int32_write(0x00000004)} {get_sector_size(head)} {head}"
    return bytes.fromhex(out_bytes)

def write_some_data(context, filepath, optimize_attempt):
    print("running write_some_data...")
    amo = get_amo(optimize_attempt)
    f = open(filepath, 'wb')
    f.write(amo)
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
