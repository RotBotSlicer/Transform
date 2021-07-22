# 3D_Printer
Algorithm for 3D printer with new printer geometry. The two scripts can be used to generate the G-Code for the RotBot printer geometry from a STL-file.

The script Transformation_STL.py takes a path to a STL-file as input, generates a mesh of a transformed object and saves this mesh in a STL file.

The script Backtransformation_GCode.py takes a path to a G-Code as input, generates G-Code for the backtransformed object and saves the G-Code in a text file.
