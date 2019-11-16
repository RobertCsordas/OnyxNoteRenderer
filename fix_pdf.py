#!/usr/bin/env python3

import numpy as np
from onyx_render import smoothen
import sys
import pdfrw
import zlib

average_win_size = 10
pressure_average_win_size = 20
n_subsample = 2
remove_onyx_metadata = False

def filter_redundant_points(plist, row_length=3):
    new_list = plist[0:row_length].copy()
    for i in range(row_length, len(plist), row_length):
        same = True
        for j in range(row_length):
            if plist[i + j] != plist[i - row_length + j]:
                same = False
                break

        if not same:
            for j in range(row_length):
                new_list.append(plist[i + j])
    return new_list

def get_stream(obj):
    if obj.Filter == "/FlateDecode":
        return zlib.decompress(obj.stream.encode('Latin-1')).decode('Latin-1')
    else:
        return obj.stream

def set_stream(obj, value):
    if obj.Filter == "/FlateDecode":
        obj.stream = zlib.compress(value.encode('Latin-1')).decode('Latin-1')
    else:
        obj.stream = value

if __name__ == "__main__":
    if len(sys.argv) not in [2,3]:
        print("Usage: %s <in pdf file> <optional: output pdf file>" % sys.argv[0])
        sys.exit(-1)

    in_file = sys.argv[1]
    save_to = sys.argv[2] if len(sys.argv)>2 else in_file

    reader = pdfrw.PdfReader(in_file, decompress=False)
    for page in reader.pages:
        if page.Annots is None:
            continue

        for a in page.Annots:
            if a.Subtype=="/PolyLine":
                if len(a.Vertices) < 4:
                    continue

                points = filter_redundant_points(a.Vertices, 2)
                points = [float(p) for p in points]

                coords = np.asfarray(points).reshape(-1,2)
                coords = smoothen(coords, average_win_size, n_subsample)

                points = coords.reshape(-1).tolist()
                points = ["%.3f" % p for p in points]

                a.Vertices = [pdfrw.PdfObject(p) for p in points]

                if remove_onyx_metadata:
                    del a["/onyxtag"]

                stream_lines = get_stream(a.AP.N).split("\n")

                line = stream_lines[1].split(" ")[0] + " w "
                line += "%s %s m " % (points[0], points[1])
                for i in range(2, len(points), 2):
                    line +="%s %s l " % (points[i], points[i+1])

                set_stream(a.AP.N, stream_lines[0]+" 1 j 1 J\n" + line + "S\n")
            elif a.onyxpoints is not None:
                # Ink with special onyx data
                points = a.onyxpoints

                plist = [float(p) for p in filter_redundant_points(get_stream(points).split(" "),3)]

                all = np.asfarray(plist).reshape(-1,3)
                coords = all[:,:2]
                pressure = all[:,2:]

                coords = smoothen(coords, average_win_size, n_subsample)
                pressure = smoothen(pressure, pressure_average_win_size, n_subsample)

                filtered = np.concatenate((coords, pressure), -1)

                plist = ["%.3f" % f for f in filtered.reshape(-1)]

                if remove_onyx_metadata:
                    del a["/onyxpoints"]
                    del a["/onyxtag"]
                else:
                    set_stream(a.onyxpoints, " ".join(plist))

                stream_lines = get_stream(a.AP.N).split("\n")
                new_lines = [stream_lines[0]+" 1 j 1 J"]

                for i in range(0, len(plist)-3, 3):
                    new_lines.append("%s w %s %s m %s %s l S" % (plist[i+2], plist[i], plist[i+1],
                                                                           plist[i+3], plist[i+4]))

                set_stream(a.AP.N, "\n".join(new_lines))

    out = pdfrw.PdfWriter(compress=True)
    out.write(save_to, trailer=reader)
