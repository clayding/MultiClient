'''
crc('123456789')
crcb(0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39)
The test gives : '0x31c3'
'''
POLYNOMIAL = 0x1021
PRESET = 0

def _initial(c):
    crc = 0
    c = c << 8
    for j in range(8):
        if (crc ^ c) & 0x8000:
            crc = (crc << 1) ^ POLYNOMIAL
        else:
            crc = crc << 1
        c = c << 1
    return crc

_tab = [ _initial(i) for i in range(256) ]

def _update_crc(crc, c):
    cc = 0xff & c

    tmp = (crc >> 8) ^ cc
    crc = (crc << 8) ^ _tab[tmp & 0xff]
    crc = crc & 0xffff

    return crc

def crc(str):
    crc = PRESET
    for c in str:
        crc = _update_crc(crc, ord(c))
    return crc

def crcb(*i):
    crc = PRESET
    for c in i:
        crc = _update_crc(crc, c)
    return crc