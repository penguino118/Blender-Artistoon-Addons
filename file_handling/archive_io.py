# pzz-unpack, decompression and compression originally written by infval
# https://github.com/infval/pzzcompressor_jojo/blob/master/pzz_comp_jojo.py
from .artistoon_import import AMO_importer
from .artistoon_import import AHI_importer
from .binary_rw import int16_read, int32_read

def load_from_pzz(context, filepath, use_z_up, user_scale):
    with open(filepath, "rb") as f:

        buffer = f.read()
        file_count = int32_read(buffer, 0x0)
        file_list = []
        read_offset = 0x4
        file_offset = 0x800
        print(f"FILECOUNT={file_count}")
        # gather all model/skeleton/animation files inside
        for file_index in range(file_count):
            file_size = int16_read(buffer, read_offset) * 0x800
            is_compressed = int16_read(buffer, read_offset+0x2) == 0x8000
            print(f"//////////////////////////////  file {file_index}: is_compressed={is_compressed} ({int16_read(buffer, read_offset)})")
            if file_size < 1: continue
            file_buffer = buffer[file_offset:file_offset+file_size]
            if is_compressed: file_buffer = get_decompressed(file_buffer)

            file_list.append({
                "buffer" : file_buffer,
                "type"   : get_filetype(file_buffer)
            })
            
            file_offset += file_size
            read_offset += 0x4
        
        # import
        for f in range(len(file_list)):
            file = file_list[f]
            match(file["type"]):
                case "AMO": 
                    # if we find a model, we'll import it
                    mesh_objects = AMO_importer.amo_read(file["buffer"], filepath, use_z_up, user_scale)
                    # then we go through and import the armature with the objects imported from the model
                    # the armature is always the file next to the model
                    if f+1 <= len(file_list):  # but just in case, we check
                        ahi_file = file_list[f+1] 
                        if ahi_file["type"] == "AHI": 
                            AHI_importer.ahi_read(ahi_file["buffer"], filepath, mesh_objects, use_z_up, user_scale)
                    
                    else:
                        # if there's no armature let's parent to an empty object instead
                        print(f"No armature found, parenting to empty")
                        import bpy
                        from os import path
                        mesh_objects = AMO_importer.amo_read(file["buffer"], filepath, use_z_up, user_scale)
                        empty = bpy.data.objects.new( f"{path.basename(filepath)[:-4]}_{f}" , None )
                        bpy.context.scene.collection.objects.link(empty)
                        for mesh in mesh_objects:
                            mesh.parent = empty
                case _: continue
                # todo: animations redo
                # pzz's file pattern allow me to know what armature belongs to what model because they're always next to each other 
                # animations don't though...... they're all shoved at the end with no reference to which skeleton they belong to
    return {'FINISHED'}


def get_filetype(buffer):
    if len(buffer) < 0x8: return ""
    read_offset = 0x0
    test_int1 = int32_read(buffer, read_offset)
    test_int2 = int32_read(buffer, read_offset+0x4)

    if test_int1 == 1 and (test_int2 == 4 or test_int2 == 3): return "AMO"
    elif test_int1 == 0xC0000000: return "AHI"
    elif test_int2 == 0x40: return "AAN" # todo: doesnt apply to player animations
    else: return "" # then we do not care


# todo: unpack_bin for auto modellista
# https://gist.github.com/penguino118/e8e2095fdd1a9ddf37f37625c414b255

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