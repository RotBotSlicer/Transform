import numpy as np
from stl import mesh
import time
import os
import sys


def refinement_one_triangle(triangle):
    """Refines one triangle into four smaller triangles."""
    point1, point2, point3 = triangle
    midpoints = (triangle + np.roll(triangle, -1, axis=0)) / 2
    return np.array([
        [point1, midpoints[0], midpoints[2]],
        [point2, midpoints[1], midpoints[0]],
        [point3, midpoints[2], midpoints[1]],
        midpoints
    ])


def refinement_triangulation(triangle_array, num_iterations):
    """Refines the entire triangulation multiple times."""
    refined_array = triangle_array
    for _ in range(num_iterations):
        refined_array = np.concatenate(
            [refinement_one_triangle(triangle) for triangle in refined_array],
            axis=0
        )
    return refined_array


def transformation_cone(points, cone_type):
    """Applies a cone transformation to an array of points."""
    c = 1 if cone_type == 'outward' else -1
    return np.array([
        [np.sqrt(2) * x, np.sqrt(2) * y, z + c * np.sqrt(x ** 2 + y ** 2)]
        for x, y, z in points
    ])


def transformation_STL_file(path, output_dir, cone_type, nb_iterations):
    """Transforms an STL file."""
    start_time = time.time()
    
    my_mesh = mesh.Mesh.from_file(path)
    vectors = my_mesh.vectors
    print(f'Initial number of triangles: {vectors.shape[0]}')

    refined_vectors = refinement_triangulation(vectors, nb_iterations)
    print(f'Refined number of triangles: {refined_vectors.shape[0]}')

    transformed_vectors = transformation_cone(refined_vectors.reshape(-1, 3), cone_type).reshape(-1, 3, 3)

    transformed_mesh = mesh.Mesh(np.zeros(transformed_vectors.shape[0], dtype=mesh.Mesh.dtype))
    transformed_mesh.vectors = transformed_vectors

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    output_path = os.path.join(output_dir, os.path.basename(path).replace('.stl', f'_{cone_type}_transformed.stl'))
    transformed_mesh.save(output_path)

    end_time = time.time()
    print(f'STL file generated in {end_time - start_time:.1f}s, saved in {output_path}')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python script.py <input_file> <output_dir>")
        sys.exit(1)

    file_path = sys.argv[1]
    dir_transformed = sys.argv[2]
    transformation_type = 'inward'  # Options: 'inward' or 'outward'
    number_iterations = 4  # Number of iterations for triangulation refinement

    transformation_STL_file(file_path, dir_transformed, transformation_type, number_iterations)
