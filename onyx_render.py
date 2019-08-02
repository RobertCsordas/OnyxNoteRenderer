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

def get_dir(dirs, parent):
    dlist = []
    while parent is not None:
        p = dirs[parent]
        parent = p["parent"]
        dlist.insert(0, p["title"])

    return os.path.join(*dlist) if dlist else ""

def read_doc_list(tmpdir):
    res = []

    conn = sqlite3.connect(os.path.join(tmpdir, "ShapeDatabase.db"))
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

    return res

def render_pdf(descriptor, tmpdir, filename):
    letter = (8.5 * 72, 11*72)

    context = cairo.PDFSurface(filename, *letter)
    scale = letter[1]
    width_scale = 0.3
    pressure_norm = 1000
    pressure_pow = 0.5
    enable_pressure = True

    conn = sqlite3.connect(os.path.join(tmpdir, descriptor["id"] + ".db"))

    cr = cairo.Context(context)
    cr.set_source_rgb(0, 0, 0)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)

    print("Rendering note %s" % descriptor["title"])
    for page in tqdm(descriptor["pages"]):
        c = conn.cursor()
        c.execute('select points, matrixValues, thickness, shapeType from NewShapeModel where pageUniqueId = "'+page+'"')

        for i, row in enumerate(c):
            # Read / parse DB entries
            points, matrix, thickness, type = row
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
            cr.set_line_width(thickness * width_scale)

            points = points * scale

            has_pressure = enable_pressure and type == 5

            for r in range(points.shape[0]):
                if has_pressure:
                    cr.set_line_width(max(thickness * width_scale * pressure[r],0.1))

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

def render_all(zip_name, save_to):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract note backup file
        with ZipFile(zip_name, 'r') as zipObj:
            zipObj.extractall(tmpdir)

        notes = read_doc_list(tmpdir)
        print("Found note structure:")
        for note in notes:
            print("   ", os.path.join(note["dirname"], note["title"]))

        for note in notes:
            dir = os.path.join(save_to, note["dirname"])
            os.makedirs(dir, exist_ok=True)
            fname = os.path.join(dir, "%s.pdf" % note["title"])

            render_pdf(note, tmpdir, fname)

if __name__ == "__main__":
    if len(sys.argv)!=3:
        print("Usage: %s <note backup file> <dir to render>" % sys.argv[0])
        sys.exit(-1)

    zip_name = sys.argv[1]
    save_to = sys.argv[2]

    render_all(zip_name, save_to)