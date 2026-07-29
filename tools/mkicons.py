import zlib, struct

BG   = (0x14, 0x18, 0x21)
BARS = [((0x2f, 0x8f, 0x83), 1.00),   # Location  teal
        ((0xd8, 0x8c, 0x2e), 0.72),   # Action    amber
        ((0x82, 0x6f, 0xdc), 0.44)]   # Detail    violet

def render(size, pad_frac):
    pad = int(size * pad_frac)
    inner = size - 2 * pad
    bar_h = int(inner * 0.20)
    gap   = int((inner - 3 * bar_h) / 2)
    rows = [[BG] * size for _ in range(size)]
    y = pad
    for color, wfrac in BARS:
        w = max(1, int(inner * wfrac))
        for yy in range(y, min(y + bar_h, size)):
            row = rows[yy]
            for xx in range(pad, min(pad + w, size)):
                row[xx] = color
        y += bar_h + gap
    return rows

def write_png(path, rows):
    h = len(rows); w = len(rows[0])
    raw = b''.join(b'\x00' + b''.join(bytes(p) for p in row) for row in rows)
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))
    blob = (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9))
            + chunk(b'IEND', b''))
    with open(path, 'wb') as fh:
        fh.write(blob)

write_png('icon-192.png',          render(192, 0.20))
write_png('icon-512.png',          render(512, 0.20))
write_png('icon-maskable-512.png', render(512, 0.29))
print('ok')
