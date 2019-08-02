# Onyx Boox note renderer

Renders PDF files from Onyx Boox Note app backup zip file.

Tested with Onyx Boox Note Pro, Firmware 2.1.2.

## What can it do?

It can read the backup file (a collection of SQLite databases) and reder PDFs out of them.

Rendering strokes with pressure sensitivity is slow.

The text transcription of each stroke is also available in the files, so it could be overlaid on the PDF in order to be searchable, but this is not done here.

## Usage

```bash
./onyx_render.py Note.zip notes 
```

It will create a new directory *notes* with the same directory structure as in the reader's Note app and render each note as a pdf inside.

It can take quite a long time, I haven't optimized for speed.

## File format

### ShapeDatabase.db 

A file describing the names and directory structure of the notes. 
Table NoteModel has many interesting fields:
```
uniqueId: the identifier of the note/directory. In case of note, this is also the filename
parentUniqueId: the uniqueId of parent directory
title: human readable filename
type: 0 - dir, 1 - note    
pageNameList: the list of page IDs in correct order. Needed to recover page order.
``` 

### UID.db

These are the individual notes, where the UID matches the uniqueId from the ShapeDatabase.db. The strokes are saved in table NewShapeModel:

```
points - a binary blog of points. See later
thickness - line thickness
matrixValues - transformation matrix
pageUniqueId - the page containing this stroke
shapeType - 5 for pressure sensitive pen, 2 for the pressure-agnostic pen
```

The transformation matrix describes an affine transformation of each point in homogeneous coordinate system. Coordinates must be projected by this matrix before rendering.

#### The points blob

This describes the actual points of the drawing. Each point uses 24 bytes of data. The first 8 are the X, Y coordinates in *big endian* float32. The next 4 is the pressure in the big endian float32. It's value seems to be between 0-6000. I haven't tried to decode the rest.