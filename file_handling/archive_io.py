# pzz-unpack, decompression and compression originally written by infval
# https://github.com/infval/pzzcompressor_jojo/blob/master/pzz_comp_jojo.py

# todo: unpack_bin for auto modellista
# https://gist.github.com/penguino118/e8e2095fdd1a9ddf37f37625c414b255

import bpy
from os import path
from pathlib import Path
from .artistoon_import import AMO_importer, AHI_importer
from .artistoon_export import AMO_exporter, AHI_exporter
from .util import natural_keys
from .binary_rw import int16_read, int32_read, int32_write, int16_write, int08_write, pad_with_byte


def pad_to_sector_size(input_bytes):  # edits list and returns entry size val
    bytes_length = len(input_bytes)
    if bytes_length <= 0:
        return input_bytes
    
    sector_size = 0
    while (sector_size * 0x800) < bytes_length:
        sector_size += 1
    padding_size = (sector_size * 0x800) - bytes_length
    
    pad_with_byte(input_bytes, 0x0, padding_size)
    return sector_size


def load_from_pzz(self, filepath, use_z_up, user_scale):
    import_count = 0
    with open(filepath, "rb") as f:

        buffer = bytearray(f.read())
        file_count = int32_read(buffer, 0x0)
        file_list = []
        read_offset = 0x4
        file_offset = 0x800
        # gather all model/skeleton/animation files inside
        for i in range(file_count):
            file_size = int16_read(buffer, read_offset) * 0x800
            is_compressed = int16_read(buffer, read_offset+0x2) == 0x8000
            if file_size < 1: continue
            file_buffer = buffer[file_offset:file_offset+file_size]
            if is_compressed: file_buffer = get_decompressed(file_buffer)

            file_list.append({
                "buffer" : file_buffer,
                "type"   : get_filetype(file_buffer),
                "compressed" : is_compressed
            })
            
            file_offset += file_size
            read_offset += 0x4
        
        # import
        if len(file_list) > 0:
            collection_name = f"{path.basename(filepath)[:-4]} File Entries"
            pzz_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(pzz_collection)

            for f, file in enumerate(file_list):
                match(file["type"]):
                    case "AMO": 
                        # if we find a model, we'll import it
                        mesh_objects = AMO_importer.amo_read(file["buffer"], f, Path(filepath).stem, use_z_up, user_scale)
                        for mesh in mesh_objects:
                            # unlink from main collection so we can link it to the pzz collection
                            bpy.context.scene.collection.objects.unlink(mesh)
                            pzz_collection.objects.link(mesh)
                            # even though we're setting the pzz entry information per object,
                            # all AMO objects will be exported as one file, so only the top mesh's
                            # info will be used on export
                            mesh.PZZ_Index = f
                            mesh.PZZ_Compressed = file["compressed"]
                        import_count += 1
                        
                        # then we go through and import the armature with the objects imported from the model
                        # the armature is always the file next to the model
                        if len(file_list) >= (f+1):  # but just in case, we check
                            next_file = file_list[f+1] 
                            if next_file["type"] == "AHI": 
                                armature = AHI_importer.ahi_read(next_file["buffer"], f+1, Path(filepath).stem, mesh_objects, use_z_up, user_scale)
                                armature.PZZ_Index = f+1
                                armature.PZZ_Compressed = next_file["compressed"]
                                # unlink armature from main scene and link to pzz collection instead
                                bpy.context.scene.collection.objects.unlink(armature)
                                pzz_collection.objects.link(armature)
                                import_count += 1
                        else:
                            # if there's no armature let's parent to an empty object instead
                            print(f"No armature found, parenting to empty")
                            mesh_objects = AMO_importer.amo_read(file["buffer"], f, Path(filepath).stem, use_z_up, user_scale)
                            empty = bpy.data.objects.new( f"{Path(filepath).stem}_{f:03}" , None )
                            empty.PZZ_Index = f
                            empty.PZZ_Compressed = file["compressed"]
                            empty.Model_Type = 'AMO'
                            pzz_collection.objects.link(empty)
                            for mesh in mesh_objects:
                                mesh.parent = empty
                                bpy.context.scene.collection.objects.unlink(mesh)
                                pzz_collection.objects.link(mesh)
                    case _: continue
                    # todo: animations redo, shadow volumes, stage collision
                    # pzz's file pattern allow me to know what armature belongs to what model because they're always next to each other 
                    # animations don't though...... they're all shoved at the end with no reference to which skeleton they belong to
    self.report({'INFO'}, f"Imported {import_count} files from the PZZ archive.")
    return {'FINISHED'}


def export_to_pzz(self, filepath, user_scale, face_type, normal_type, uv_split, use_z_up):
    if not path.isfile(filepath):
        self.report({'ERROR'}, f"Cannot save collection objects into a PZZ that doesn't already exist.")
        return {'CANCELLED'}
    
    # get entries from collection objects
    collection = bpy.context.view_layer.active_layer_collection.collection
    print(f"Exporting collection: {collection.name}")
    file_replacements = []
    for object in collection.objects:
        amo_mesh_objects = []
        hits_mesh_objects = [] # todo: this
        sdt_mesh_objects = [] # todo: implement shadow volume i/o

        if object.type != 'ARMATURE' and object.type != 'EMPTY':
            continue #raise Exception(f"Exported collection has a root object that isn't an armature or empty! ({object.name})")

        for child in object.children:
            if child.type == 'MESH':
                match(child.data.Export_Type):
                    case 'AMO': amo_mesh_objects.append(child)
                    case 'HITS': hits_mesh_objects.append(child)
                    case 'SDT': sdt_mesh_objects.append(child)
        
        amo_mesh_objects = sorted(amo_mesh_objects[:], key=lambda obj: natural_keys(obj.name))

        # get model data
        armature_bytes, armature_entry, bone_list = AHI_exporter.get_ahi(object, use_z_up, user_scale, amo_mesh_objects) # should return empty if the object isn't an armature
        model_bytes, model_entry = AMO_exporter.get_amo(amo_mesh_objects, bone_list, uv_split, face_type, normal_type, user_scale, use_z_up)
        
        for export, entry_info in zip(
            [model_bytes, armature_bytes], 
            [model_entry, armature_entry]):
            if len(export) > 0:
                file_replacements.append({
                    "index" : entry_info["index"],
                    "compressed" : entry_info["compressed"],
                    "bytes" : export
                })
    
    buffer = bytearray()
    with open(filepath, "rb") as f:
        buffer = bytearray(f.read())

        header_offset = 0x4
        for replacement in file_replacements:
            file_index = replacement["index"]
            is_compressed = replacement["compressed"]
            new_file_data = replacement["bytes"]
            
            if is_compressed:
                new_file_data = get_compressed(new_file_data)
            sector_size = pad_to_sector_size(new_file_data)
            
            # get offset of file to replace
            current_offset = 0x800  # skip header
            for i in range(file_index):
                sector_count = int16_read(buffer, header_offset + (i * 0x4))
                current_offset += sector_count * 0x800
            
            original_sector_count = int16_read(buffer, header_offset + (file_index * 0x4))
            original_file_size = original_sector_count * 0x800
            print(f"Replacing file {file_index} at {hex(current_offset)}:{hex(current_offset + original_file_size)}")
            buffer[current_offset:current_offset + original_file_size] = new_file_data
            
            # update header entry
            entry_offset = header_offset + (file_index * 0x4)
            buffer[entry_offset:entry_offset+2] = int16_write(sector_size)
            compression_flag = 0x8000 if is_compressed else 0
            buffer[entry_offset+2:entry_offset+4] = int16_write(compression_flag)

    with open(filepath, "wb") as f:
        f.write(buffer)

    self.report({'INFO'}, f"Written {len(file_replacements)} to the PZZ archive.")
    return {'FINISHED'}


def get_filetype(buffer):
    if len(buffer) < 0x8: return ""
    read_offset = 0x0
    test_int1 = int32_read(buffer, read_offset)
    test_int2 = int32_read(buffer, read_offset+0x4)

    if test_int1 == 1 and (test_int2 > 2 and test_int2 < 6): return "AMO" # model data
    elif test_int1 == 0xC0000000: return "AHI" # bone data
    elif test_int2 == 0x40: return "AAN" # animation data -- todo: doesnt apply to player file animations
    elif test_int2 == 0x50000: return "SDT" # shadow data
    elif test_int1 == 0x53544948: return "HITS" # stage collision data
    else: return "" # then we do not care


def get_decompressed(b):
    bout = bytearray()
    size_b = len(b) // 2 * 2

    cb = 0  # Control bytes
    cb_bit = -1
    i = 0
    while i < size_b:
        if cb_bit < 0:
            cb  = b[i + 0]
            cb |= b[i + 1] << 8
            cb_bit = 15
            i += 2
            continue

        compress_flag = cb & (1 << cb_bit)
        cb_bit -= 1

        if compress_flag:
            c  = b[i + 0]
            c |= b[i + 1] << 8
            offset = (c & 0x7FF) * 2
            if offset == 0:
                break # End of the compressed data
            count = (c >> 11) * 2
            if count == 0:
                i += 2
                c  = b[i + 0]
                c |= b[i + 1] << 8
                count = c * 2

            index = len(bout) - offset
            for j in range(count):
                bout.append(bout[index + j])
        else:
            bout.extend(b[i: i + 2])
        i += 2

    return bout


def get_compressed(b):
    bout = bytearray()
    size_b = len(b) // 2 * 2

    cb = 0  # Control bytes
    cb_bit = 15
    cb_pos = 0
    bout.extend(b"\x00\x00")

    i = 0
    while i < size_b:
        start = max(i - 0x7FF * 2, 0)
        count_r = 0
        max_i = -1
        tmp = b[i: i + 2]
        init_count = len(tmp)
        while True:
            start = b.find(tmp, start, i + 1)
            if start != -1 and start % 2 != 0:
                start += 1
                continue
            if start != -1:
                count = init_count
                while i < size_b - count \
                    and count < 0xFFFF * 2 \
                    and b[start + count    ] == b[i + count    ] \
                    and b[start + count + 1] == b[i + count + 1]:
                    count += 2
                if count_r < count:
                    count_r = count
                    max_i = start
                start += 2
            else:
                break
        start = max_i

        compress_flag = 0
        if count_r >= 4:
            compress_flag = 1
            offset = i - start
            offset //= 2
            count_r //= 2
            c = offset
            if count_r <= 0x1F:
                c |= count_r << 11
                bout.append(c & 0xFF)
                bout.append((c >> 8))
            else:
                bout.append(c & 0xFF)
                bout.append((c >> 8))
                bout.append(count_r & 0xFF)
                bout.append((count_r >> 8))
            i += count_r * 2
        else:
            bout.extend(b[i: i + 2])
            i += 2
        cb |= (compress_flag << cb_bit)
        cb_bit -= 1
        if cb_bit < 0:
            bout[cb_pos + 0] = cb & 0xFF
            bout[cb_pos + 1] = cb >> 8
            cb = 0x0000
            cb_bit = 15
            cb_pos = len(bout)
            bout.extend(b"\x00\x00")

    cb |= (1 << cb_bit)
    bout[cb_pos + 0] = cb & 0xFF
    bout[cb_pos + 1] = cb >> 8
    bout.extend(b"\x00\x00")

    return bout