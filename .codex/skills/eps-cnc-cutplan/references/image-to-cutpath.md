# Image to CutPath

Images never release production directly.

Workflow:

1. Store the image path in `project.source.image_path`.
2. Set `source.kind=image_reference`.
3. Set `scale_confirmed=false`, `dimensions_confirmed=false`, and `production_confirmed=false`.
4. Generate a draft YAML and preview only.
5. Require at least one real-world dimension before calculating pixel/mm.
6. Require human confirmation before generating test DXF.

OpenCV contour extraction should start from threshold/Canny binary images, then simplify contours with a recorded tolerance. The result is a draft path, not final machine geometry.
