import struct


# WRITE #

def int16_write(int):
    return struct.pack('<H', int)

def int32_write(int):
    return struct.pack('<I', int)

def int32_write_signed(int):
    return struct.pack('<i', int)
    
def float_write(float):
    return struct.pack('<f', float)
    
def int32_write_list(list):
    tmpb = []
    for x in list:
        tmpb.append(struct.pack('<I', x))
    return tmpb

def pad_bytes(input_list, input_byte, size):
    l = [input_byte] * (size//4)
    for v in l:
        input_list.append(int32_write(v))
        

# READ #

def int08_read(buf, offset):
    return struct.unpack("<B", buf[offset:offset+1])[0]

def int16_read(buf, offset):
    return struct.unpack("<H", buf[offset:offset+2])[0]

def int16_read_signed(buf, offset):
    return struct.unpack("<h", buf[offset:offset+2])[0]

def int32_read(buf, offset):
    return struct.unpack("<I", buf[offset:offset+4])[0]

def float_read(buf, offset):
    return struct.unpack("<f", buf[offset:offset+4])[0]