import numpy as np
from stl import mesh
import time
import os
import argparse


def transformation_kegel(points, cone_angle_rad, cone_type):
    """
    Computes the cone-transformation (x', y', z') = (x / cos(angle), y / cos(angle), z + \sqrt{x^{2} + y^{2}} * tan(angle))
    for a list of points
    :param points: array
        array of points of shape ( , 3)
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :return: array
        array of transformed points, of same shape as input array
    """
    if cone_type == 'outward':
        c = 1
    elif cone_type == 'inward':
        c = -1
    else:
        raise ValueError('{} is not a admissible type for the transformation'.format(cone_type))
    f = (lambda x, y, z: np.array([x/np.cos(cone_angle_rad), y/np.cos(cone_angle_rad), z + c * np.sqrt(x**2 + y**2)*np.tan(cone_angle_rad)]))
    points_transformed = list(map(f, points[:, 0], points[:, 1], points[:, 2]))
    return np.array(points_transformed)


def refinement_four_triangles(triangle):
    """
    Compute a refinement of a triangle. On every side, the midpoint is added. The three corner points and three
    midpoints result in four smaller triangles.
    :param triangle: array
        array of three points of shape (3, 3) (one triangle)
    :return: array
        array of shape (4, 3, 3) of four triangles
    """
    point1 = triangle[0]
    point2 = triangle[1]
    point3 = triangle[2]
    midpoint12 = (point1 + point2) / 2
    midpoint23 = (point2 + point3) / 2
    midpoint31 = (point3 + point1) / 2
    triangle1 = np.array([point1, midpoint12, midpoint31])
    triangle2 = np.array([point2, midpoint23, midpoint12])
    triangle3 = np.array([point3, midpoint31, midpoint23])
    triangle4 = np.array([midpoint12, midpoint23, midpoint31])
    return np.array([triangle1, triangle2, triangle3, triangle4])


def refinement_triangulation(triangle_array, num_iterations):
    """
    Compute a refinement of a triangulation using the refinement_four_triangles function.
    The number of iteration defines, how often the triangulation has to be refined; n iterations lead to
    4^n times many triangles.
    :param triangle_array: array
        array of shape (num_triangles, 3, 3) of triangles
    :param num_iterations: int
    :return: array
        array of shape (num_triangles*4^num_iterations, 3, 3) of triangles
    """
    refined_array = triangle_array
    for i in range(0, num_iterations):
        n_triangles = refined_array.shape[0]*4
        refined_array = np.array(list(map(refinement_four_triangles, refined_array)))
        refined_array = np.reshape(refined_array, (n_triangles, 3, 3))
    return refined_array


def transformation_STL_file(path, cone_type, cone_angle_deg, nb_iterations):
    """
    Read a stl-file, refine the triangulation and transform it according to the cone-transformation
    :param path: string
        path to the stl file
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :param cone_angle: int
        angle to transform the part
    :param nb_iterations: int
        number of iterations, the triangulation should be refined before the transformation
    :return: mesh object
        transformed triangulation as mesh object which can be stored as stl file
    """
    cone_angle_rad = cone_angle_deg / 180 * np.pi
    my_mesh = mesh.Mesh.from_file(path)
    vectors = my_mesh.vectors
    vectors_refined = refinement_triangulation(vectors, nb_iterations)
    vectors_refined = np.reshape(vectors_refined, (-1, 3))
    vectors_transformed = transformation_kegel(vectors_refined, cone_angle_rad, cone_type)
    vectors_transformed = np.reshape(vectors_transformed, (-1, 3, 3))
    my_mesh_transformed = np.zeros(vectors_transformed.shape[0], dtype=mesh.Mesh.dtype)
    my_mesh_transformed['vectors'] = vectors_transformed
    my_mesh_transformed = mesh.Mesh(my_mesh_transformed)
    return my_mesh_transformed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Conical Transform', description='Conical Transformation - Variable angle', formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=80))
    parser.add_argument('-f', '--file', type=str, required=True, help='Relative or absolute path to the .stl file (ie. tower_01_-20)')
    parser.add_argument('-o', '--output', type=str, default='stl_transformed',  help='Folder in which to save transformed .stl file')
    parser.add_argument('-a', '--angle', type=int, default=16,  help='Transformation angle')
    parser.add_argument('-i', '--iterations', type=int, default=1, help='Refinement iterations of the stl')
    parser.add_argument('-r', '--reverse', action='store_true', default=False,  help='Reverse transformation type (set this flag for inward transformation)')
    parser.add_argument('--absolute', action='store_true', default=False,  help='Force use of absolute paths')
    args = parser.parse_args()

    # Check if file exists
    if not os.path.exists(args.file):
        print("File `{}` does not exist!".format(args.file))
        print("Aborting.")
        exit()
    # Check if right extension
    elif not args.file.lower().endswith('.stl'):
        print("Unsupported file type. Expected '.stl' (file:`{}`)!".format(args.file))
        print("Aborting.")
        exit()

    # Check if output folder exists
    if not os.path.exists(args.output):
        print("Output folder `{}` does not exist. Creating...".format(args.output))
        try:
            os.mkdir(args.output)
        except Exception as e:
            print(e)
            print("Failed to create directory `{}`".format(args.output))
            exit()

    # Set transformation type
    if not args.reverse:
        transformation_type = 'outward'
    else:
        transformation_type = 'inward'

    # Create new file name for transformed file
    output_file_name = os.path.basename(args.file)
    if output_file_name.lower().endswith('.stl'):
        output_file_name = output_file_name.replace('.stl', '')
    # Pattern is: (filename)_transformed_(transformation-type)_(cone-angle)deg_transformed.stl
    output_file_name = "{}_transformed_{}_{}deg.stl".format(output_file_name, transformation_type, args.angle)
    output_file_path = os.path.join(args.output, output_file_name)

    # Force use of absolute paths (convenience and debugging)
    if args.absolute:
        args.file = os.path.abspath(args.file)
        output_file_path = os.path.abspath(output_file_path)

    # Print requested parameters
    print('-'*50)
    print("Transforming:\t\t{}".format(args.file))
    print("Saving output to:\t{}".format(output_file_path))
    print("Cone angle:\t\t{}".format(args.angle))
    print("Refinement iterations:\t{}".format(args.iterations))
    print("Transformation type:\t{}".format(transformation_type))
    print('-'*50)

    # Begin transformation
    print('Starting transformation... (this could take a while)')
    start_time = time.time()
    transformed_STL = transformation_STL_file(path=args.file, cone_type=transformation_type, cone_angle_deg=args.angle, nb_iterations=args.iterations)
    transformed_STL.save(output_file_path)
    end_time = time.time()
    print('Done.')
    print('Transformation took {} seconds'.format( round(end_time-start_time, 2) ))
