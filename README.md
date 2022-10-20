# 3D_Printer

### Introduction
This is an algorithm for a 3D printer with new printer kinematics. With this new printer kinematics, overhangs with 90° and more can be printed without support material. The two scripts can be used to generate the G-Code for the RotBot printer kinematics from a STL-file. The algorithm is based on a geometric transformation of the body. The ideas are summarized in [https://www.researchgate.net/publication/354726760_A_Novel_Slicing_Strategy_to_Print_Overhangs_without_Support_Material](). 

The script Transformation_STL.py takes a path to a STL-file as input, generates a mesh of a transformed object and saves this mesh in a STL file.

The script Backtransformation_GCode.py takes a path to a G-Code as input, generates G-Code for the backtransformed object and saves the G-Code in a text file.

To generate G-Code from the STL file, different slicer software can be used, e.g. [https://ultimaker.com/software/ultimaker-cura]() or [https://www.simplify3d.com/]()

### Transformation of the STL file
The transformation of the STL file has the following parameters:
* file_path: path to the STL file of the body
* dir_transformed: path, where to save the STL file of the transformed body 
* transformation_type: 'inward' or 'outward' transformation
* nb_iterations: number iterations for the triangulation refinement

On the command line:
```
python Transformation_STL.py -i 3DBenchy.stl -o out -t inward -n 1
```


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
* e_perpendicular: extrusion error to correct in perpendicular direction

Type the following command to perform the backtransformation:
```
python Backtransformation_GCode.py -i 3DBenchy_mod.gcode -o out
```

### Scripts for variable angle
With this scripts, the cone angle can be changed. So it does not only work for 45° angle as used for RotBot, but can also be used with much smaller angles (e.g. 15°) to do a conical slicing for any printer. So overhangs can be printed on any printer.

### License
The algorithm is open source and licensed under the GNU General Public License Version 3.0 ([https://www.gnu.org/licenses/gpl-3.0.en.html]()).

### Citation
If you use the algorithm, please consider citing the following paper:
```
@Article{app11188760,
AUTHOR = {Wüthrich, Michael and Gubser, Maurus and Elspass, Wilfried J. and Jaeger, Christian},
TITLE = {A Novel Slicing Strategy to Print Overhangs without Support Material},
JOURNAL = {Applied Sciences},
VOLUME = {11},
YEAR = {2021},
NUMBER = {18},
ARTICLE-NUMBER = {8760},
URL = {https://www.mdpi.com/2076-3417/11/18/8760},
ISSN = {2076-3417},
ABSTRACT = {Fused deposition modeling (FDM) 3D printers commonly need support material to print overhangs. A previously developed 4-axis printing process based on an orthogonal kinematic, an additional rotational axis around the z-axis and a 45° tilted nozzle can print overhangs up to 100° without support material. With this approach, the layers are in a conical shape and no longer parallel to the printing plane; therefore, a new slicer strategy is necessary to generate the paths. This paper describes a slicing algorithm compatible with this 4-axis printing kinematics. The presented slicing strategy is a combination of a geometrical transformation with a conventional slicing software and has three basic steps: Transformation of the geometry in the .STL file, path generation with a conventional slicer and back transformation of the G-code. A comparison of conventionally manufactured parts and parts produced with the new process shows the feasibility and initial results in terms of surface quality and dimensional accuracy.},
DOI = {10.3390/app11188760}
}
```
