import bpy
import struct
import bmesh
from collections import defaultdict
import math
import mathutils
from mathutils import Matrix, Vector, Color
from bpy_extras import io_utils, node_shader_utils
from bpy_extras.wm_utils.progress_report import (
    ProgressReport,
    ProgressReportSubstep,
)

bl_info = {
    "name": "Artistoon Model Exporter",
    "description": "Exporter for the Artistoon Model Format (AMO) found in GioGio's Bizarre Adventure.",
    "author": "Penguino",
    "version": (1, 0),
    "blender": (3, 4, 1),
    "location": "File > Export",
    "warning": "", # used for warning icon and text in addons panel
    "category": "Export",
}

#amodelmagic = 1      #AMO filehead
unknwnmagic = 131072 #unknown (ram position?)
#mdcontmagic = 2      #model container
#mscontmagic = 4      #mesh container
#tscontmagic = 5      #tri strip container
trismagic03 = 196608 #tri strips with 1 or no bone influence
trismagic04 = 262144 #tri strips with 2 bone influence
mtlistmagic = 327680 #material list
mtlprsmagic = 393216 #material per strip
vertexmagic = 458752 #vertex coordinates
normalmagic = 524288 #vertex normals
vertUVmagic = 655360 #vertex UVs
vcolormagic = 720896 #vertex colors
weightmagic = 786432 #vertex weights
gboundmagic = 1114112 #bounding model fetch
attribmagic = 983040 #mesh attributes
    #mtlsetmagic = 9      #material header?
    #txheadmagic = 10     #texture header

def write_some_data(context, filepath, attrib, amomat, tim2res, oktris, okweight, cull0x10):
    # Triangle Strip
    def gettristrips(mesh, allmats):
        TMPstrip = []
        indices03 = []
        indices04 = []
        strips03 = ""
        strips04 = ""
        teststrip = []
        facemat03 = []
        facemat04 = []
        #calculate weights first to decide where faces will go

        tmpvg = []
        twoinflist = []
        bones = ""

        texcount = len(matlist)
        
        for vertex in mesh.vertices:
            #print("Vertex: ", vertex.index)
            for group in vertex.groups:
                vgroup_name = obj.vertex_groups[group.group].name
                vgroup_weight = group.weight
                tmpvg.append(vgroup_name)
                tmpvg.append(vgroup_weight)
            if len(tmpvg) == 4:
                twoinflist.append(vertex.index)
                print(f"(!!!) Vertex {vertex.index} has 2 group influence")
            tmpvg.clear()
        
        for face in mesh.polygons:
            vc=len(face.vertices)
            for x in face.vertices:
                TMPstrip.append(f"{intb(x)}")
                teststrip.append(x)
            if any(item in twoinflist for item in teststrip):
                indices04.append(f"{vc}{face.vertices[0:]}")
                facemat04.append(f"{mesh.materials[face.material_index].name}")
                strips04 += (f" {intb(vc)} ")
                for x in TMPstrip:
                    strips04 += (f"{x} ") 
            else:
                indices03.append(f"{vc}{face.vertices[0:]}")
                facemat03.append(f"{mesh.materials[face.material_index].name}")
                strips03 += (f"{intb(vc)}")
                for x in TMPstrip:
                    strips03 += (f"{x} ") 
            TMPstrip.clear()
            teststrip.clear()

        print(f"(EXPERIMENTAL) Strips (Type 04): {indices04}")
        print(f"(EXPERIMENTAL) Strips (Type 03): {indices03}")
        tris04count = len(indices04)
        tris03count = len(indices03)

        tris04array = (f"{intb(trismagic04)} {intb(tris04count)} {getsizebytes(strips04)} {strips04}")
        tris03array = (f"{intb(trismagic03)} {intb(tris03count)} {getsizebytes(strips03)} {strips03}")
        facemat = ""
        mattexlist = []
        for x in range(texcount):
            mattexlist.append(x)
        matindex03 = ""
        matindex04 = ""
        for x in facemat04:
            for m in matlist:
                if x == m:
                    matindex04 += (f"{intb(matlist.index(m))} ")
        for x in facemat03:
            for m in matlist:
                if x == m:
                    matindex03 += (f"{intb(matlist.index(m))} ")
        facemat = (f"{matindex04} {matindex03}")
        matperstrip = f"{intb(393216)} {intb(tris04count + tris03count)} {getsizebytes(facemat)} {facemat}"
        matFinal= f"{intb(327680)} {intb(texcount)} {getsizebytes(batchint(mattexlist))} {batchint(mattexlist)} {matperstrip}"

        if len(strips04) > 0:
            #print("Wrote 04 and 03 type strips")
            tristrips = (f"{tris04array} {tris03array}")
            out = f"{intb(5)} {intb(2)} {getsizebytes(tristrips)} {tristrips} {matFinal}"
        elif len(strips04) == 0:
            #print("No 04 strips written")
            out = f"{intb(5)} {intb(1)} {getsizebytes(tris03array)} {tris03array} {matFinal}"
        return out
    
    def getvertcoords(mesh):
        print(f"Vert Count: {vertexcount}")
        #print("Vert Coord: ")
        vcoords = ""
        for vert in mesh.vertices:
            xyz = vert.co.xyz
            #print(f"{round(xyz[1],7):<{10}}, {round(xyz[2],7):<{10}}, {round(xyz[0],7):<{10}}")
            vcoords += f"{floatb(xyz[1])} {floatb(xyz[2])} {floatb(xyz[0])} " #blender's y is z in gio
        out = f"{intb(vertexmagic)} {intb(vertexcount)} {getsizebytes(vcoords)} {vcoords}"
        return out

    def getnormals(mesh):
        #print(f"Normal Count: {vertexcount}")
        #print("Normals: ")
        norms = ""
        for vert in mesh.vertices:
            vnorm = vert.normal
            #print(f"{round(vnorm[1],7):<{10}}, {round(vnorm[2],7):<{10}}, {round(vnorm[0],7):<{10}}")
            norms += f"{floatb(vnorm[1])} {floatb(vnorm[2])} {floatb(vnorm[0])} "
        out = f"{intb(normalmagic)} {intb(vertexcount)} {getsizebytes(norms)} {norms}"
        return out

    def singleUV(intindex):
        tmpuv = None
        for face in obj.data.polygons:
            for vertindex, loopindex in zip(face.vertices, face.loop_indices):
                uv_coords = obj.data.uv_layers.active.data[loopindex].uv
                if vertindex == intindex:
                    tmpuv = uv_coords
        return tmpuv

    def getUVs(mesh):
        uvcoords = ""
        uv = []
        for x in range(vertexcount):
            if singleUV(x) is not None:
                uv = (singleUV(x)[0], singleUV(x)[1])
            uvcoords += f"{floatb(uv[0])} {floatb(1-uv[1])} "
            print(f"Vertex {x} UV: {round(uv[0],3):<{5}}, {round(uv[1],3):<{5}}")
        out = f"{intb(vertUVmagic)} {intb(vertexcount)} {getsizebytes(uvcoords)} {uvcoords}"
        return out

    def getcolors(mesh):
        #print("Color Attributes: ")
        colors = ""
        if obj.data.attributes.active_color is not None:
            for i in obj.data.attributes.active_color.data:
                cR= clamp(i.color[0] * 255, 0, 255)
                cG= clamp(i.color[1] * 255, 0, 255)
                cB= clamp(i.color[2] * 255, 0, 255)
                cA= clamp(i.color[3] * 255, 0, 255)
                print(f"R: {round(cR,3):<{8}}, G: {round(cG,3):<{8}}, B: {round(cB,3):<{8}}, A: {round(cA,3):<{8}}")
                colors += f"{floatb(cR)} {floatb(cG)} {floatb(cB)} {floatb(cA)} "
            out = f"{intb(vcolormagic)} {intb(vertexcount)} {getsizebytes(colors)} {colors}"
            return out
        else:
            print("No active color attributes found, writing 255,255,255,255 instead.")
            for x in range(vertexcount):
                colors += f"{floatb(255)} {floatb(255)} {floatb(255)} {floatb(255)} "
            out = f"{intb(vcolormagic)} {intb(vertexcount)} {getsizebytes(colors)} {colors}"
            return out

    def getvweights(mesh):
        tmpvg = []
        bones = ""
        out = ""
        for vertex in mesh.vertices:
            print("Vertex: ", vertex.index)
            for group in vertex.groups:
                vgroup_name = obj.vertex_groups[group.group].name
                vgroup_weight = group.weight
                print("  Group: ", vgroup_name, " Weight: ", vgroup_weight)
                tmpvg.append(vgroup_name)
                tmpvg.append(vgroup_weight)
            if len(tmpvg) == 0:
                print("No weights detected for any group! Aborting.")
                break
            if len(tmpvg) == 4:
                bones+= f"02000000 {intb(int(tmpvg[0], 16))} {floatb(tmpvg[1]*100)} {intb(int(tmpvg[2], 16))} {floatb(tmpvg[3]*100)} "
            if len(tmpvg) == 2:
                bones+= f"01000000 {intb(int(tmpvg[0], 16))} {floatb(tmpvg[1]*100)} "
            tmpvg.clear()
        if len(bones) > 0:
            out = f"{intb(weightmagic)} {intb(vertexcount)} {getsizebytes(bones)} {bones}"
        return out

    def writeattributes(type, cull0x10):
        out = ""
        end = [2, 3 ,0 ,0 , 0, 0, 0]
        
        player =  [65536, 1, 0, 0, 0, 0, 0, 0, 1, 1, 6]
        playerp = [65536, 1, 0, 0, 0, 2, 0, 0, 1, 1, 0]
        npc =     [65536, 1, 0, 1, 0, 2, 0, 0, 1, 1, 0]
        ui =      [65536, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]
        other =   [65536, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0]
        if type == 'player':
            print("Writing Playermodel attributes...")
            attribs = (f"{batchint(player)}{batchint(end)}")
        elif type == 'playerp':
            print("Writing Playermodel Part attributes...")
            attribs = (f"{batchint(playerp)}{batchint(end)}")
        elif type == 'npc':
            print("Writing NPC model attributes...")
            attribs = (f"{batchint(npc)}{batchint(end)}")
        elif type == 'ui':
            print("Writing UI model attributes...")
            attribs = (f"{batchint(ui)}{batchint(end)}")
        else:
            print("Writing generic model attributes...")
            attribs = (f"{batchint(other)}{batchint(end)}")
        if cull0x10 == True:
            attribs = attribs[:37] + '1' + attribs[38:]
        out = f"{intb(attribmagic)} {intb(1)} {getsizebytes(attribs)} {attribs}"
        return out

    def writematerials(count, type, res):
        out = ""
        print("(EXPERIMENTAL) Writing Materials")
        repeat = False
        if type == 'generic':
            type = 1
        elif type == 'overlay':
            type = 2
        elif type == 'shadeless':
            type = 3
        elif type == 'static':
            type = 5
        elif type == 'effect':
            type = 0
        else:
            type = 1
        
        mathead  = (f"{intb(type)} {intb(1)} {intb(272)}")
        
        #resolution values
        res128 = [ 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 50.0 ]
        res256 = [ 0.5, 0.5, 0.5, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 50.0 ]
        res512 = [ 1.0, 1.0, 1.0, 1.0, 0.699999, 0.699999, 0.699999, 1.0, 1.0, 1.0, 0.0, 0.0, 50.0 ]
        
        #padding
        l = [0] * 50
        pad = ""
        for v in l:
            pad += (f"{intb(v)}")
        
        print(f"res: {res}")
        for n in range(count):
            if res == '128':
                print("Adding material with resolution \"128\"")
                out += (f"{intb(type)} {intb(1)} {intb(272)} {batchfloat(res128)} {intb(1)} {pad} {intb(n)} ")
            elif res == '256':
                print("Adding material with resolution \"256\"")
                out += (f"{intb(type)} {intb(1)} {intb(272)} {batchfloat(res256)} {intb(1)} {pad} {intb(n)} ")
            elif res == '512':
                print("Adding material with resolution \"512\"")
                out += (f"{intb(type)} {intb(1)} {intb(272)} {batchfloat(res512)} {intb(1)} {pad} {intb(n)} ")
                    
        out = (f"{intb(9)} {intb(count)} {getsizebytes(out)} {out}")
        
        
        #texhead sector ( 0A 00 00 00 )
        texhead = (f"{intb(0)} {intb(1)} {intb(268)}")
        #padding
        print(f"res: {tim2res} / mat: {amomat}")
        l = [0] * 61
        pad = ""
        for v in l:
            pad += (f"{intb(v)}")
        texindex = ""
        for n in range(count):
            if res == '128':
                print(f"Adding texture with resolution \"128\" (count {n})")
                texindex += (f"{texhead} {intb(n)} {intb(128)} {intb(128)} {pad}")
            elif res == '256':
                print(f"Adding texture with resolution \"256\" (count {n})")
                texindex += (f"{texhead} {intb(n)} {intb(256)} {intb(256)} {pad}")
            elif res == '512':
                print(f"Adding texture with resolution \"512\" (count {n})")
                texindex += (f"{texhead} {intb(n)} {intb(512)} {intb(512)} {pad}")
        if texindex == "":
            print("Erm... what the devil...")
        texheadbytes = (f"{intb(10)} {intb(count)} {getsizebytes(texindex)} {texindex}")
        out = (f"{out} {texheadbytes}")
        return out

    active_collection = bpy.context.view_layer.active_layer_collection.collection
    meshcount = len([obj for obj in active_collection.objects if obj.type == 'MESH'])
    print(f"Mesh count in selected collection ({active_collection.name}): {meshcount}")
    matlist = []
    meshobj = ""
    container = ""
    for obj in active_collection.objects: #lets get materials first
        meshdata = ""
        if obj.type == 'MESH':
            print(f"**Gathering materials.... Mesh: \"{obj.name}\"**")
            mesh = obj.data
            for material in mesh.materials:
                if material.name in matlist:
                    print(f"mat {material.name} already exists in matlist ({matlist})")
                    pass
                else:
                    matlist.append(material.name)
            
    for obj in active_collection.objects: #ok now we get mesh data
        meshdata = ""
        if obj.type == 'MESH':
            print(f"**Processing mesh \"{obj.name}\"**")
            mesh = obj.data
            vertexcount=len(mesh.vertices)
            if oktris == True:
                meshdata += (gettristrips(mesh, matlist))
            meshdata += (getvertcoords(mesh))
            meshdata += (getnormals(mesh))
            meshdata += (getUVs(mesh))
            meshdata += (getcolors(mesh))
            if okweight == True:
                meshdata += (getvweights(mesh))
            meshdata += (writeattributes(attrib, cull0x10))
            meshobj += (f"{intb(4)} {intb(9)} {getsizebytes(meshdata)} {meshdata} ")
    modelcontainer = (f"{intb(2)} {intb(meshcount)} {getsizebytes(meshobj)} {meshobj}")
    unkhead = [131072, 1, 16, 17500416]
    matdata = (writematerials(len(matlist), amomat, tim2res))
    AMOwrap = (f"{batchint(unkhead)} {modelcontainer} {matdata}")
    finalbytes = (f"{intb(1)} {intb(4)} {getsizebytes(AMOwrap)} {AMOwrap}")
    print("Export finished.")
    out = open(filepath, 'wb')
    out.write(bytes.fromhex(finalbytes))
    out.close()

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class AMOexport(Operator, ExportHelper):
    """Export collections as Artistoon Model files"""
    bl_idname = "export_scene.amo"
    bl_label = "Export AMO"

    # ExportHelper mixin class uses this
    filename_ext = ".amo"

    filter_glob: StringProperty(
        default="*.amo;*.bin",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    
    #bpy.types.Scene.Collection = bpy.props.EnumProperty(items=get_collections)
    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    
    
    attributes: EnumProperty(
        name="Attributes",
        description="Choose between model attributes.",
        items=(
            ('player', "Playermodel", "Attributes used for Playermodels"),
            ('playerp', "Playermodel Part", "Attributes used for Playermodel Part models"),
            ('npc', "NPC model", "Attributes used for NPC models"),
            ('ui', "UI element", "Attributes used for models used in UI elements"),
            ('other', "Other", "Attributes used for miscellaneous models"),
        ),
        default='player',
    )
    
    mat_attributes: EnumProperty(
        name="Material",
        description="Set up material properties.",
        items=(
            ('generic', "General", "Commonly used in playermodels"),
            ('overlay', "Overlay", "Used in speech bubble and onomatopeia"),
            ('shadeless', "Shadeless", "Used in some NPC models"),
            ('static', "Static", "Used in most UI elements"),
            ('effect', "Effect", "Used for special effect elements"),
        ),
        default='generic',
    )
    
    tim2_res: EnumProperty(
        name="Texture Resolution",
        description="Define the resolution of the textures.",
        items=(
            ('128', "128x128 px", "128 pixel width and height."),
            ('256', "256x256 px", "256 pixel width and height."),
            ('512', "512x512 px", "512 pixel width and height."),
        ),
        default='256',
    )
    
    use_strips: BoolProperty(
        name="Generate Tri-Strips",
        description="Generate triangle strip from faces. Fast but highly inneficient."
            "(WARNING! experimental option, use at own risks, known broken with armatures/animations)",
        default=True,
    )
    
    use_weights: BoolProperty(
        name="Export Weights",
        description="Export Vertex Weights. Only up to two groups can influence a vertex.",
        default=True,
    )
    
    cullmode: BoolProperty(
        name="Disable Culling",
        description="(WARNING! experimental option, disables culling when mesh is outside of the screen)",
        default=False,
    )

    def execute(self, context):
        write_some_data(context, self.filepath, self.attributes, self.mat_attributes, self.tim2_res, self.use_strips, self.use_weights, self.cullmode)
        self.report({'INFO'}, 'AMO Export finished.')
        return {'FINISHED'}


def intb(int):
    tmpb = f"{struct.unpack('>I', struct.pack('<I', int))[0]:08X}"
    return tmpb

def floatb(float):
    tmpb = f"{struct.unpack('>I', struct.pack('<f', float))[0]:08X}"
    return tmpb
    
def batchint(list):
    tmpb = ""
    for x in list:
        tmpb += f"{struct.unpack('>I', struct.pack('<I', x))[0]:08X} "
    return tmpb

def batchfloat(list):
    tmpb = ""
    for x in list:
        tmpb += f"{struct.unpack('>I', struct.pack('<f', x))[0]:08X} "
    return tmpb

def getsizebytes(array):
    tmpb = len(bytes.fromhex(f"{intb(1)} {intb(1)} {intb(1)} {array}"))
    tmpb = intb(tmpb)
    return tmpb

def clamp(value, minimum, maximum):
  return max(minimum, min(value, maximum))

# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(AMOexport.bl_idname, text="Artistoon Model (.amo)")

# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
def register():
    bpy.utils.register_class(AMOexport)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(AMOexport)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_scene.amo('INVOKE_DEFAULT')
