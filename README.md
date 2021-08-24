# 3D_Printer

### Introduction
This is an algorithm for a 3D printer with new printer kinematics. With this new printer kinematics, overhangs with 90° and more can be printed without support material. The two scripts can be used to generate the G-Code for the RotBot printer kinematics from a STL-file. The algorithm is based on a geometric transformation of the body. The ideas are summarized in REFERENZ (tbd). 

The script Transformation_STL.py takes a path to a STL-file as input, generates a mesh of a transformed object and saves this mesh in a STL file.

The script Backtransformation_GCode.py takes a path to a G-Code as input, generates G-Code for the backtransformed object and saves the G-Code in a text file.

To generate G-Code from the STL file, different slicer software can be used, e.g. [https://ultimaker.com/software/ultimaker-cura]() or [https://www.simplify3d.com/]()

### Transformation of the STL file
The transformation of the STL file has the following parameters:
* file_path: path to the STL file of the body
* dir_transformed: path, where to save the STL file of the transformed body 
* transformation_type: 'inward' or 'outward' transformation
* nb_iterations: number iterations for the triangulation refinement

### Back-Transformation of the G-Code
The back-transformation of the G-Code has the following parameters:
* file_path: path to the G-Code
* dir_backtransformed: path, where the transformed G-Code should be saved
* transformation_type: 'inward' or 'outward' transformation
* angle_type: 'radial' or 'tangential' orientation of the print head
* max_length: maximal length of a segment in mm
* x_shift: shift of (final) G-code in x-direction
* y_shift: shift of (final) G-code in y-direction
* z_desired: desired height in z-direction
* e_parallel: extrusion error to correct in parallel direction
* e_perpenticular: extrusion error to correct in perpendicular direction

### License
The algorithm is open source and licensed under the GNU General Public License Version 3.0 ([https://www.gnu.org/licenses/gpl-3.0.en.html]()).

### Citation
If you use the algorithm, please consider citing the following paper:
```
@article{wuethrich2021slicing,
  title        = {Slicing Strategy for a novel 4-Axis 3D Printing Process to Print Overhangs without Support Material},
  author       = {Michael Wüthrich, Maurus Gubser, Wilfried J. Elspass, Christian Jaeger},
  journal      = {Applied Sciences},
  volume       = {},
  number       = {},
  pages        = {},
  year         = {2021},
  publisher    = {MDPI}
}
```
