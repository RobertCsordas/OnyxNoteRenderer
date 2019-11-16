#!/usr/bin/env python3

import tempfile
from zipfile import ZipFile
import sqlite3
import os
import json
import numpy as np
from tqdm import tqdm
import sys
import cairo
import math
import traceback
from smoothen import smoothen

width_scale = 0.3
pressure_norm = 1000
pressure_pow = 0.5
enable_pressure = True
n_subsample = 2
min_thickness = 0.5
average_win_size = 10
pressure_average_win_size = 20

DEBUG=False

def get_dir(dirs, parent):
    dlist = []
    while parent is not None:
        p = dirs[parent]
        parent = p["parent"]
        dlist.insert(0, p["title"])

    return os.path.join(*dlist) if dlist else ""

def read_doc_list(tmpdir):
    res = []

    conn = sqlite3.connect(os.path.join(tmpdir, "ShapeDatabase.db"), uri=True)
    c = conn.cursor()
    c.execute('select uniqueId,title,parentUniqueId from NoteModel where type = 0')
    dirs = {}
    for row in c:
        id, title, parent = row
        dirs[id] = {"title": title, "parent": parent}

    c = conn.cursor()
    c.execute('select uniqueId,title,pageNameList,parentUniqueId from NoteModel where type = 1')
    for row in c:
        id, title, namelist, parent = row
        namelist = json.loads(namelist)["pageNameList"]

        res.append({"id": id, "title": title, "pages": namelist,
                    "dirname": get_dir(dirs, parent)})

    conn.close()
    return res

def render_pdf(descriptor, tmpdir, filename):
    letter = (8.5 * 72, 11*72)

    with cairo.PDFSurface(filename, *letter) as context:
        scale = letter[1]

        conn = sqlite3.connect(os.path.join(tmpdir, descriptor["id"] + ".db"), uri=True)

        cr = cairo.Context(context)
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        prev_color = (0,0,0)
        prev_thickness = 0

        print("Rendering note %s" % descriptor["title"])
        for page in tqdm(descriptor["pages"]):
            c = conn.cursor()
            c.execute('select points, matrixValues, thickness, shapeType, color from NewShapeModel where pageUniqueId = "'+page+'"')

            for i, row in enumerate(c):
                # Read / parse DB entries
                points, matrix, thickness, type, color = row
                if matrix is None:
                    # Compatibility with older note format
                    matrix = np.eye(3,3)
                else:
                    matrix = np.asarray(json.loads(matrix)["values"], dtype=np.float32).reshape(3,3)

                d = np.frombuffer(points, dtype=np.float32)
                d = d.byteswap()

                d = d.reshape(-1, 6)

                pressure = (d[:,2] / pressure_norm) ** pressure_pow
                # Projection matrix
                points = d[:, :2]
                points = np.concatenate((points, np.ones([points.shape[0],1])), axis=1)
                points = points @ matrix.T
                points = points[:, :2]

                # Draw
                thickness_changed = prev_thickness != thickness
                if thickness_changed:
                    cr.stroke()
                    prev_thickness = thickness
                    cr.set_line_width(thickness * width_scale)

                color = color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF
                color_changed = color != prev_color
                if (color_changed):
                    cr.stroke()
                    prev_color = color
                    cr.set_source_rgb(color[2]/255, color[1]/255, color[0]/255);

                points = points * scale

                has_pressure = enable_pressure and type == 5

                points = smoothen(points, average_win_size, n_subsample)
                pressure = smoothen(pressure, pressure_average_win_size, n_subsample)

                for r in range(points.shape[0]):
                    if has_pressure:
                        cr.set_line_width(max(thickness * width_scale * pressure[r], min_thickness))

                    if r==0:
                        cr.move_to(points[r][0], points[r][1])
                    else:
                        cr.line_to(points[r][0], points[r][1])

                        if has_pressure:
                            # Must do separate strokes to change thickness.
                            cr.stroke()
                            cr.move_to(points[r][0], points[r][1])

            cr.stroke()
            cr.show_page()

        conn.close()

def render(zip_name, save_to, names):
    if names is not None:
        names = names.split(",")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract note backup file
        with ZipFile(zip_name, 'r') as zipObj:
            zipObj.extractall(tmpdir)

        notes = read_doc_list(tmpdir)
        print("Found note structure:")
        for note in notes:
            print("   ", os.path.join(note["dirname"], note["title"]))

        for note in notes:
            full_note_name = os.path.join(note["dirname"], note["title"])

            if names is not None and full_note_name not in names:
                continue

            dir = os.path.join(save_to, note["dirname"])
            os.makedirs(dir, exist_ok=True)
            fname = os.path.join(dir, "%s.pdf" % note["title"])

            try:
                render_pdf(note, tmpdir, fname)
            except:
                print("Failed to render %s" % full_note_name)
                if os.path.exists(fname):
                    os.remove(fname)
                if DEBUG:
                    traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) not in [3,4]:
        print("Usage: %s <note backup file> <dir to render> <optional: names of doc to render, split by ,>" % sys.argv[0])
        sys.exit(-1)

    zip_name = sys.argv[1]
    save_to = sys.argv[2]
    names = None if len(sys.argv)<4 else sys.argv[3]

    render(zip_name, save_to, names)