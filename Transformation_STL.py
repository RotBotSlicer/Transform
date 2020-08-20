import numpy as np
from stl import mesh
import time


def refinement_one_triangle(triangle):
    """
    Compute a refinement of one triangle. On every side, the midpoint is added. The three corner points and three
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
        refined_array = np.array(list(map(refinement_one_triangle, refined_array)))
        refined_array = np.reshape(refined_array, (n_triangles, 3, 3))
    return refined_array


def transformation_cone(points, cone_type):
    """
    Compute the cone-transformation (x', y', z') = (\sqrt{2}x, \sqrt{2}y, z + \sqrt{x^{2} + y^{2}}) ('outward') or
    (x', y', z') = (\sqrt{2}x, \sqrt{2}y, z - \sqrt{x^{2} + y^{2}}) ('inward') for a list of points
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
    T = (lambda x, y, z: np.array([np.sqrt(2)*x, np.sqrt(2)*y, z + c * np.sqrt(x**2 + y**2)]))
    points_transformed = list(map(T, points[:, 0], points[:, 1], points[:, 2]))
    return np.array(points_transformed)


def transformation_STL_file(path, cone_type, nb_iterations):
    """
    Read a stl-file, refine the triangulation and transform it according to the cone-transformation
    :param path: string
        path to the stl file
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :param nb_iterations: int
        number of iterations, the triangulation should be refined before the transformation
    :return: mesh object
        transformed triangulation as mesh object which can be stored as stl file
    """
    my_mesh = mesh.Mesh.from_file(path)
    vectors = my_mesh.vectors
    vectors_refined = refinement_triangulation(vectors, nb_iterations)
    vectors_refined = np.reshape(vectors_refined, (-1, 3))
    vectors_transformed = transformation_cone(vectors_refined, cone_type)
    vectors_transformed = np.reshape(vectors_transformed, (-1, 3, 3))
    my_mesh_transformed = np.zeros(vectors_transformed.shape[0], dtype=mesh.Mesh.dtype)
    my_mesh_transformed['vectors'] = vectors_transformed
    my_mesh_transformed = mesh.Mesh(my_mesh_transformed)
    return my_mesh_transformed


# -------------------------------------------------------------------------------
# Apply the functions for a STL file
# -------------------------------------------------------------------------------


filename = 'Wuerfel_high_low'
foldername_original = 'STL_Modelle/'
foldername_transformed = 'Modelle_Transformiert_Kegel/'
filepath = foldername_original + filename + '.stl'
transformation_type = 'inward'

start = time.time()
transformed_STL = transformation_STL_file(path=filepath, cone_type=transformation_type, nb_iterations=4)
transformed_STL.save(foldername_transformed + filename + '_' + transformation_type + '_transformed.stl')
end = time.time()
print('STL file generated, time needed:', end - start)
