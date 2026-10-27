"""Turns the supplied Samsung wordmark (black on white) into transparent black and white PNGs for assets/brand/.
Usage: python3 scripts/build-brand-assets.py <supplied-logo.png>"""
import sys, zlib, struct

def read(path):
    d = open(path, 'rb').read(); p = 8; idat = b''
    while p < len(d):
        l, t = struct.unpack('>I4s', d[p:p + 8]); b = d[p + 8:p + 8 + l]; p += 12 + l
        if t == b'IHDR': w, h, _, ct = struct.unpack('>IIBB', b[:10])
        if t == b'IDAT': idat += b
    ch = {6: 4, 2: 3, 0: 1, 4: 2}[ct]; raw = zlib.decompress(idat); st = w * ch; prev = bytearray(st); rows = []; i = 0
    for _ in range(h):
        f = raw[i]; ln = bytearray(raw[i + 1:i + 1 + st]); i += 1 + st
        for x in range(st):
            a = ln[x - ch] if x >= ch else 0; b_ = prev[x]; c = prev[x - ch] if x >= ch else 0
            if f == 1: ln[x] = (ln[x] + a) & 255
            elif f == 2: ln[x] = (ln[x] + b_) & 255
            elif f == 3: ln[x] = (ln[x] + (a + b_) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b_ - c), abs(a - c), abs(a + b_ - 2 * c)
                ln[x] = (ln[x] + (a if pa <= pb and pa <= pc else (b_ if pb <= pc else c))) & 255
        rows.append(ln); prev = ln
    return w, h, ch, rows

def write(path, w, h, rows):
    def chunk(t, b): return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

w, h, ch, rows = read(sys.argv[1])
for name, rgb in (('samsung-logo-black', (0, 0, 0)), ('samsung-logo-white', (255, 255, 255))):
    out = []
    for r in rows:
        o = bytearray()
        for x in range(0, w * ch, ch):
            o += bytes(rgb) + bytes([255 - r[x]])  # darkness of the pixel becomes its opacity
        out.append(o)
    write(f'assets/brand/{name}.png', w, h, out)
print('ok', w, h)
