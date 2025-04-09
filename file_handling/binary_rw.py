import struct


# WRITE #
def int08_write(int):
    return struct.pack('<B', int)

def int16_write(int):
    return struct.pack('<H', int)

def int32_write(int):
    return struct.pack('<I', int)

def int32_write_signed(int):
    return struct.pack('<i', int)
    
def float_write(float):
    return struct.pack('<f', float)

def pad_with_byte(input_list, input_byte, size):
    l = [input_byte] * (size)
    for v in l:
        input_list.extend(int08_write(v))
        

# READ #

def int08_read(buf, offset):
    return struct.unpack("<B", buf[offset:offset+1])[0]

def int16_read(buf, offset):
    return struct.unpack("<H", buf[offset:offset+2])[0]

def int16_read_signed(buf, offset):
    return struct.unpack("<h", buf[offset:offset+2])[0]

def int32_read(buf, offset):
    return struct.unpack("<I", buf[offset:offset+4])[0]

def int32_read_signed(buf, offset):
    return struct.unpack("<i", buf[offset:offset+4])[0]

def float_read(buf, offset):
    return struct.unpack("<f", buf[offset:offset+4])[0]