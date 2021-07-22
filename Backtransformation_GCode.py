import re
import numpy as np
import os
import time


def insert_Z(row, z_value):
    """
    Insert or replace the z-value in a row. The new z-value must be given.
    :param row: string
        String containing the row, in which a z-value has to be inserted or replaced
    :param z_value: float
        New z-value, which should be inserted
    :return: string
        New string, containing the row with replaced z-value
    """
    pattern_X = r'X[-0-9]+[.]?[0-9]*'
    pattern_Y = r'Y[-0-9]+[.]?[0-9]*'
    pattern_Z = r'Z[-0-9]+[.]?[0-9]*'
    match_x = re.search(pattern_X, row)
    match_y = re.search(pattern_Y, row)
    match_z = re.search(pattern_Z, row)

    if match_z is not None:
        row_new = re.sub(pattern_Z, ' Z' + str(round(z_value, 3)), row)
    else:
        if match_y is not None:
            row_new = row[0:match_y.end(0)] + ' Z' + str(round(z_value, 3)) + row[match_y.end(0):]
        elif match_x is not None:
            row_new = row[0:match_x.end(0)] + ' Z' + str(round(z_value, 3)) + row[match_x.end(0):]
        else:
            row_new = 'Z' + str(round(z_value, 3)) + ' ' + row
    return row_new


def replace_E(row, dist_old, dist_new, corr_value):
    """
    Replace the amount of extruded filament in a row. The new amount is proportional to the old amount, where
    the factor is obtained by the ratio of new distance to old distance. (Due to the transformation, the amount has to be divided by sqrt(2). replace_E is accessed 2 times.)
    :param row: string
        String containing the row, of which the extruder value should be replaced
    :param dist_old: float
        Length of the distance before backtransformation
    :param dist_new: float
        Length of the distance after backtransformation
    :param corr_value: float
        additional correction value due to transformation	# added to have additional possiblity to correct amount of extruded material
    :return: string
        New string, containing the row with replaced extruder value
    """
    pattern_E = r'E[-0-9]+[.]?[0-9]*'
    match_e = re.search(pattern_E, row)
    if match_e is None:
        return row
    e_val_old = float(match_e.group(0).replace('E', ''))
    if dist_old == 0:
        e_val_new = 0
    else:
        e_val_new = round(e_val_old * dist_new * corr_value / dist_old, 6)
    e_str_new = 'E' + str(e_val_new)
    row_new = row[0:match_e.start(0)] + e_str_new + row[match_e.end(0):]
    return row_new


def compute_angle_radial(x_new, y_new, inward_cone):
    """
    Compute the angle of the printing head, when moving from an old point [x_old, y_old] to a new point [x_new, y_new].
    (Note: the z-value is not considered for the orientation of the printing head.) The direction is given by the
    direction of the new point by the arctan2 value according to the coordinates.
    :param x_new: float
        x-coordinate of the new point
    :param y_new: float
        y-coordinate of the new point
    :param inward_cone: bool
        Boolean variable, which depends on the kind of transformation. If True, an additional angle of pi is added to
        the angle.
    :return: float
        Angle, which describes orientation of printing head. Its value lies in [-pi, pi].
    """
    angle = np.arctan2(y_new, x_new)
    if inward_cone:
        angle = angle + np.pi
    return angle


def compute_angle_tangential(x_old, y_old, x_new, y_new, inward_cone):
    """
    Compute the angle of the printing head, when moving from an old point [x_old, y_old] to a new point [x_new, y_new].
    (Note: the z-value is not considered for the orientation of the printing head.) The direction is normal to the
    movement of direction, such that the printing head will point to the origin.
        x-coordinate of the old point
    :param x_old: float
        x-coordinate of the old point
    :param y_old: float
        y-coordinate of the old point
    :param x_new: float
        x-coordinate of the new point
    :param y_new: float
        y-coordinate of the new point
    :param inward_cone: bool
        Boolean variable, which depends on the kind of transformation. If True, an additional angle of pi is added to
        the angle.
    :return: float
        Angle, which describes orientation of printing head. Its value lies in [-pi, pi].
    """
    direction_normal = np.array([-(y_new - y_old), x_new - x_old])
    len_normal = np.linalg.norm(direction_normal)
    direction_point = np.array([x_new, y_new])
    len_point = np.linalg.norm(direction_point)
    if len_normal * len_point == 0:
        angle = np.arctan2(y_new, x_new)
    else:
        inner_prod = np.dot(direction_normal / len_normal, direction_point / len_point)
        if np.isclose(inner_prod, 0, atol=0.01):
            angle = np.arctan2(direction_normal[1], direction_normal[0])
        else:
            printhead_direction = inner_prod * len_point / len_normal * direction_normal
            angle = np.arctan2(printhead_direction[1], printhead_direction[0])

    if inward_cone:
        angle = angle + np.pi

    return angle


def compute_angle_mixed(x_old, y_old, x_new, y_new, inward_cone, visible_print):
    """
    Compute the angle of the printing head, when moving from an old point [x_old, y_old] to a new point [x_new, y_new].
    (Note: the z-value is not considered for the orientation of the printing head.) When printing an inner layer, the
    angle is given by the direction of the new point by the arctan2 value according to the coordinates. When printing
    an outer layer, the angle is computed using the tangential part of the movement.
    :param x_old: float
        x-coordinate of the old point
    :param y_old: float
        y-coordinate of the old point
    :param x_new: float
        x-coordinate of the new point
    :param y_new: float
        y-coordinate of the new point
    :param inward_cone: bool
        Boolean variable, which depends on the kind of transformation. If True, an additional angle of pi is added to
        the angle.
    :param visible_print: bool
        Bool, which defines, if the angle has to be computed for a outer layer
    :return: float
        Angle, which describes orientation of printing head. Its value lies in [-pi, pi].
    """
    if visible_print is False:
        angle = np.arctan2(y_new, x_new)
    else:
        direction_normal = np.array([-(y_new - y_old), x_new - x_old])
        len_normal = np.linalg.norm(direction_normal)
        direction_point = np.array([x_new, y_new])
        len_point = np.linalg.norm(direction_point)
        if len_normal * len_point == 0:
            angle = np.arctan2(y_new, x_new)
        else:
            inner_prod = np.dot(direction_normal / len_normal, direction_point / len_point)
            if np.isclose(inner_prod, 0, atol=0.01):
                angle = np.arctan2(direction_normal[1], direction_normal[0])
            else:
                printhead_direction = inner_prod * len_point / len_normal * direction_normal
                angle = np.arctan2(printhead_direction[1], printhead_direction[0])

    if inward_cone:
        angle = angle + np.pi

    return angle


def compute_U_values(angle_array):
    """
    Compute the U-values, which will be inserted, according to given angle values. The U-values are computed such that
    there are no changes larger than 180. The range of the U-values is [-3600-180, 3600+180].
    :param angle_array: array
        Array, which contains the angle values in radian
    :return array
        Array, which contains U-values in degrees
    """
    angle_candidates = np.around(np.array([angle_array + k * 2 * np.pi for k in range(-10, 11)]).T, 4)
    angle_insert = [angle_array[0]]
    for i in range(1, len(angle_array)):
        angle_prev = angle_insert[i - 1]
        idx = np.argmin(np.absolute(angle_candidates[i] - angle_prev))
        angle_insert.append(angle_candidates[i, idx])

    angle_insert = np.round(np.array(angle_insert) * 360 / (2 * np.pi), 2)

    return angle_insert


def insert_U(row, angle):
    """
    Insert or replace the U-value in a row, where the U-values describes the orientation of the printing head.
    :param row: string
        String containing the row, in which a U-value has to be inserted or replaced
    :param angle: float
        Value of the angle, which is inserted or replaces the old U-value
    :return: string
        New string, containing the row with replaced U-value
    """
    pattern_Z = r'Z[-0-9]+[.]?[0-9]*'
    match_z = re.search(pattern_Z, row)
    pattern_U = r'U[-0-9]+[.]?[0-9]*'
    match_u = re.search(pattern_U, row)

    if match_u is None:
        row_new = row[0:match_z.end(0)] + ' U' + str(angle) + row[match_z.end(0):]
    else:
        row_new = re.sub(pattern_U, 'U' + str(angle), row)

    return row_new


def backtransform_data_radial(data, cone_type, maximal_length):
    """
    Backtransform G-Code, which is given in a list, each element describing a row. Rows which describe a movement
    are detected, x-, y-, z-, E- and U-values are replaced accordingly to the transformation. If a original segment
    is too long, it gets divided into sub-segments before the backtransformation. The U-values are computed
    using the function compute_angle_radial. (Added, that while travel moves, nozzle only rises 1 mm above highest printed point and not along cone.)
    :param data: list
        List of strings, describing each line of the GCode, which is to be backtransformed
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :param maximal_length: float
        Maximal length of a segment in the original GCode; every longer segment is divided, such that the resulting
        segments are shorter than maximal_length
    :return: list
        List of strings, which describe the new GCode.
    """
    new_data = []
    pattern_X = r'X[-0-9]+[.]?[0-9]*'
    pattern_Y = r'Y[-0-9]+[.]?[0-9]*'
    pattern_Z = r'Z[-0-9]+[.]?[0-9]*'
    pattern_E = r'E[-0-9]+[.]?[0-9]*'
    pattern_G = r'\AG[01] '

    x_old, y_old = 0, 0
    x_new, y_new = 0, 0
    z_layer = 0
    angle_old = 0
    z_max = 0
    update_x, update_y = False, False
    visible_print = False
    if cone_type == 'outward':
        c = -1
        inward_cone = False
    elif cone_type == 'inward':
        c = 1
        inward_cone = True
    else:
        raise ValueError('{} is not a admissible type for the transformation'.format(cone_type))

    for row in data:

        g_match = re.search(pattern_G, row)
        if g_match is None:
            new_data.append(row)

        else:
            x_match = re.search(pattern_X, row)
            y_match = re.search(pattern_Y, row)
            z_match = re.search(pattern_Z, row)
            if x_match is None and y_match is None and z_match is None:
                new_data.append(row)

            else:
                if z_match is not None:
                    z_layer = float(z_match.group(0).replace('Z', ''))
                if x_match is not None:
                    x_new = float(x_match.group(0).replace('X', ''))
                    update_x = True
                if y_match is not None:
                    y_new = float(y_match.group(0).replace('Y', ''))
                    update_y = True

                # Compute new distance and angle according to new row
                e_match = re.search(pattern_E, row)
                x_old_bt, x_new_bt = x_old / np.sqrt(2), x_new / np.sqrt(2)
                y_old_bt, y_new_bt = y_old / np.sqrt(2), y_new / np.sqrt(2)
                dist_transformed = np.linalg.norm([x_new - x_old, y_new - y_old])

                # Compute new values for backtransformation of row
                num_segm = int(dist_transformed // maximal_length + 1)
                x_vals = np.linspace(x_old_bt, x_new_bt, num_segm + 1)
                y_vals = np.linspace(y_old_bt, y_new_bt, num_segm + 1)
                if inward_cone and e_match is None and (update_x or update_y):
                    z_start = z_layer + c * np.sqrt(x_old_bt ** 2 + y_old_bt ** 2)
                    z_end = z_layer + c * np.sqrt(x_new_bt ** 2 + y_new_bt ** 2)
                    z_vals = np.linspace(z_start, z_end, num_segm + 1)
                else:
                    z_vals = np.array([z_layer + c * np.sqrt(x ** 2 + y ** 2) for x, y in zip(x_vals, y_vals)])
                    if e_match and (np.max(z_vals) > z_max or z_max == 0):
                        z_max = np.max(z_vals) # save hightes point with material extruded
                    if e_match is None and np.max(z_vals) > z_max:
                        np.minimum(z_vals, (z_max + 1), z_vals)	# cut away all travel moves, that are higher than max height extruded + 1 mm safety
                        # das hier könnte noch verschönert werden, in dem dann eine alle abgeschnittenen Werte mit einer einer geraden Linie ersetzt werden

                angle_new = compute_angle_radial(x_old_bt, y_old_bt, x_new_bt, y_new_bt, inward_cone)

                angle_vals = np.array([angle_old] + [compute_angle_radial(x_vals[k], y_vals[k], x_vals[k + 1], y_vals[k + 1], inward_cone) for k in range(0, num_segm)])
                u_vals = compute_U_values(angle_vals)
                distances_transformed = dist_transformed / num_segm * np.ones(num_segm)
                distances_bt = np.array([np.linalg.norm([x_vals[i] - x_vals[i - 1], y_vals[i] - y_vals[i - 1], z_vals[i] - z_vals[i - 1]]) for i in range(1, num_segm + 1)])

                # Replace new row with num_seg new rows for movements and possible command rows for the U value
                row = insert_Z(row, z_vals[0])
                row = replace_E(row, num_segm, 1, 1 / np.sqrt(2))
                replacement_rows = ''
                for j in range(0, num_segm):
                    single_row = re.sub(pattern_X, 'X' + str(round(x_vals[j + 1], 3)), row)
                    single_row = re.sub(pattern_Y, 'Y' + str(round(y_vals[j + 1], 3)), single_row)
                    single_row = re.sub(pattern_Z, 'Z' + str(round(z_vals[j + 1], 3)), single_row)
                    single_row = replace_E(single_row, distances_transformed[j], distances_bt[j], 1)
                    if np.abs(u_vals[j + 1] - u_vals[j]) <= 30:
                        single_row = insert_U(single_row, u_vals[j + 1])
                    else:
                        single_row = 'G1 E-0.800 \n' + 'G1 U' + str(u_vals[j + 1]) + ' \n' + 'G1 E0.800 \n' + single_row
                    replacement_rows = replacement_rows + single_row
                if np.amax(np.absolute(u_vals)) > 3600:
                    angle_reset = np.round(angle_vals[-1] * 360 / (2 * np.pi), 2)
                    replacement_rows = replacement_rows + 'G92 U' + str(angle_reset) + '\n'
                    angle_old = angle_new
                else:
                    angle_old = u_vals[-1] * 2 * np.pi / 360
                row = replacement_rows

                if update_x:
                    x_old = x_new
                    update_x = False
                if update_y:
                    y_old = y_new
                    update_y = False
                new_data.append(row)

    return new_data


def backtransform_data_tangential(data, cone_type, maximal_length):
    """
   Backtransform GCode, which is given in a list, each element describing a row. Rows which describe a movement
    are detected, x-, y-, z-, e- and U-values are replaced accordingly to the transformation. If a original segment
    is too long, it gets divided into sub-segments before the backtransformation. The U-values are computed
    using the function compute_angle_tangential.
    :param data: list
        List of strings, describing each line of the GCode, which is to be backtransformed
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :param maximal_length: float
        Maximal length of a segment in the original GCode; every longer segment is divided, such that the resulting
        segments are shorter than maximal_length
    :return: list
        List of strings, which describe the new GCode.
    """
    new_data = []
    pattern_X = r'X[-0-9]+[.]?[0-9]*'
    pattern_Y = r'Y[-0-9]+[.]?[0-9]*'
    pattern_Z = r'Z[-0-9]+[.]?[0-9]*'
    pattern_E = r'E[-0-9]+[.]?[0-9]*'
    pattern_G = r'\AG[01] '

    x_old, y_old = 0, 0
    x_new, y_new = 0, 0
    z_layer = 0
    angle_old = 0
    z_max = 0

    update_x, update_y = False, False
    if cone_type == 'outward':
        c = -1
        inward_cone = False
    elif cone_type == 'inward':
        c = 1
        inward_cone = True
    else:
        raise ValueError('{} is not a admissible type for the transformation'.format(cone_type))

    for row in data:

        g_match = re.search(pattern_G, row)
        if g_match is None:
            new_data.append(row)

        else:
            x_match = re.search(pattern_X, row)
            y_match = re.search(pattern_Y, row)
            z_match = re.search(pattern_Z, row)

            if x_match is None and y_match is None and z_match is None:
                new_data.append(row)

            else:
                if z_match is not None:
                    z_layer = float(z_match.group(0).replace('Z', ''))
                if x_match is not None:
                    x_new = float(x_match.group(0).replace('X', ''))
                    update_x = True
                if y_match is not None:
                    y_new = float(y_match.group(0).replace('Y', ''))
                    update_y = True

                # Compute new values according to new row
                e_match = re.search(pattern_E, row)
                x_old_bt, y_old_bt = x_old / np.sqrt(2), y_old / np.sqrt(2)
                x_new_bt, y_new_bt = x_new / np.sqrt(2), y_new / np.sqrt(2)
                dist_transformed = np.linalg.norm([x_new - x_old, y_new - y_old])
                if update_x or update_y:
                    angle_new = compute_angle_tangential(x_old_bt, y_old_bt, x_new_bt, y_new_bt, inward_cone)
                else:
                    angle_new = angle_old

                # Compute new values for backtransformation of row
                num_segm = int(dist_transformed // maximal_length + 1)
                x_vals = np.linspace(x_old_bt, x_new_bt, num_segm + 1)
                y_vals = np.linspace(y_old_bt, y_new_bt, num_segm + 1)
                if inward_cone and e_match is None and (update_x or update_y):
                    z_start = z_layer + c * np.sqrt(x_old_bt ** 2 + y_old_bt ** 2)
                    z_end = z_layer + c * np.sqrt(x_new_bt ** 2 + y_new_bt ** 2)
                    z_vals = np.linspace(z_start, z_end, num_segm + 1)
                else:
                    z_vals = np.array([z_layer + c * np.sqrt(x ** 2 + y ** 2) for x, y in zip(x_vals, y_vals)])
                    if e_match and (np.max(z_vals) > z_max or z_max == 0):
                        z_max = np.max(z_vals) # save hightes point with material extruded
                    if e_match is None and np.max(z_vals) > z_max:
                        np.minimum(z_vals, (z_max + 1), z_vals)	# cut away all travel moves, that are higher than max height extruded + 1 mm safety
                        # das hier könnte noch verschönert werden, in dem dann alle abgeschnittenen Werte mit einer einer geraden Linie ersetzt werden
                angle_vals = np.array([angle_old] + [angle_new for k in range(0, num_segm)])
                u_vals = compute_U_values(angle_vals)
                distances_transformed = dist_transformed / num_segm * np.ones(num_segm)
                distances_bt = np.array(
                    [np.linalg.norm([x_vals[i] - x_vals[i - 1], y_vals[i] - y_vals[i - 1], z_vals[i] - z_vals[i - 1]])
                     for i in range(1, num_segm + 1)])

                # Replace new row with num_seg new rows for movements and possible command rows for the U value
                row = insert_Z(row, z_vals[0])
                row = replace_E(row, num_segm, 1, 1 / np.sqrt(2))
                replacement_rows = ''
                for j in range(0, num_segm):
                    single_row = re.sub(pattern_X, 'X' + str(round(x_vals[j + 1], 3)), row)
                    single_row = re.sub(pattern_Y, 'Y' + str(round(y_vals[j + 1], 3)), single_row)
                    single_row = re.sub(pattern_Z, 'Z' + str(round(z_vals[j + 1], 3)), single_row)
                    single_row = replace_E(single_row, distances_transformed[j], distances_bt[j],1)
                    if np.abs(u_vals[j + 1] - u_vals[j]) <= 30:
                        single_row = insert_U(single_row, u_vals[j + 1])
                    else:
                        single_row = single_row + 'G1 E-0.800 \n' + 'G1 U' + str(u_vals[j + 1]) + ' \n' + 'G1 E0.800 \n'
                    replacement_rows = replacement_rows + single_row
                if np.amax(np.absolute(u_vals)) > 3600:
                    angle_reset = np.round(angle_vals[-1] * 360 / (2 * np.pi), 2)
                    replacement_rows = replacement_rows + 'G92 U' + str(angle_reset) + '\n'
                    angle_old = angle_new
                else:
                    angle_old = u_vals[-1] * 2 * np.pi / 360

                row = replacement_rows

                if update_x:
                    x_old = x_new
                    update_x = False
                if update_y:
                    y_old = y_new
                    update_y = False
                new_data.append(row)

    return new_data


def backtransform_data_mixed(data, cone_type, maximal_length):
    """
    Backtransform GCode, which is given in a list, each element describing a row. Rows which describe a movement
    are detected, x-, y-, z-, e- and U-values are replaced accordingly to the transformation. If a original segment
    is too long, it gets divided into sub-segments before the backtransformation. The u-values are computed using
    the function compute_angle_mixed, i.e. the computation depends, if a infill or a visible layer is printed.
    :param data: list
        List of strings, describing each line of the GCode, which is to be backtransformed
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :param maximal_length: float
        Maximal length of a segment in the original GCode; every longer segment is divided, such that the resulting
        segments are shorter than maximal_length
    :return: list
        List of strings, which describe the new GCode.
    """
    new_data = []
    pattern_X = r'X[-0-9]+[.]?[0-9]*'
    pattern_Y = r'Y[-0-9]+[.]?[0-9]*'
    pattern_Z = r'Z[-0-9]+[.]?[0-9]*'
    pattern_E = r'E[-0-9]+[.]?[0-9]*'
    pattern_G = r'\AG[01] '
    pattern_outer = r'; feature outer perimeter'
    pattern_inner = r'; feature inner perimeter'
    pattern_comment = r'; feature'

    x_old, y_old = 0, 0
    x_new, y_new = 0, 0
    z_layer = 0
    angle_old = 0
    update_x, update_y = False, False
    visible_print = False
    if cone_type == 'outward':
        c = -1
        inward_cone = False
    elif cone_type == 'inward':
        c = 1
        inward_cone = True
    else:
        raise ValueError('{} is not a admissible type for the transformation'.format(cone_type))

    for row in data:
        outer_match = re.search(pattern_outer, row)
        inner_match = re.search(pattern_inner, row)
        comment_match = re.search(pattern_comment, row)
        if outer_match is not None or inner_match is not None:
            visible_print = True
        if visible_print and comment_match is not None and outer_match is None and inner_match is None:
            visible_print = False

        g_match = re.search(pattern_G, row)
        if g_match is None:
            new_data.append(row)

        else:
            x_match = re.search(pattern_X, row)
            y_match = re.search(pattern_Y, row)
            z_match = re.search(pattern_Z, row)

            if x_match is None and y_match is None and z_match is None:
                new_data.append(row)

            else:
                if z_match is not None:
                    z_layer = float(z_match.group(0).replace('Z', ''))
                if x_match is not None:
                    x_new = float(x_match.group(0).replace('X', ''))
                    update_x = True
                if y_match is not None:
                    y_new = float(y_match.group(0).replace('Y', ''))
                    update_y = True

                # Compute new values according to new row
                e_match = re.search(pattern_E, row)
                x_old_bt, y_old_bt = x_old / np.sqrt(2), y_old / np.sqrt(2)
                x_new_bt, y_new_bt = x_new / np.sqrt(2), y_new / np.sqrt(2)
                dist_transformed = np.linalg.norm([x_new - x_old, y_new - y_old])
                angle_new = compute_angle_mixed(x_old_bt, y_old_bt, x_new_bt, y_new_bt, inward_cone, visible_print)

                # Compute new values for backtransformation of row
                num_segm = int(dist_transformed // maximal_length + 1)
                x_vals = np.linspace(x_old_bt, x_new_bt, num_segm + 1)
                y_vals = np.linspace(y_old_bt, y_new_bt, num_segm + 1)
                if inward_cone and e_match is None and (update_x or update_y):
                    z_start = z_layer + c * np.sqrt(x_old_bt ** 2 + y_old_bt ** 2)
                    z_end = z_layer + c * np.sqrt(x_new_bt ** 2 + y_new_bt ** 2)
                    z_vals = np.linspace(z_start, z_end, num_segm + 1)
                else:
                    z_vals = np.array([z_layer + c * np.sqrt(x ** 2 + y ** 2) for x, y in zip(x_vals, y_vals)])
                    if e_match and (np.max(z_vals) > z_max or z_max == 0):
                        z_max = np.max(z_vals) # save hightes point with material extruded
                    if e_match is None and np.max(z_vals) > z_max:
                        np.minimum(z_vals, (z_max + 1), z_vals)	# cut away all travel moves, that are higher than max height extruded + 1 mm safety
                        # das hier könnte noch verschönert werden, in dem dann eine alle abgeschnittenen Werte mit einer einer geraden Linie ersetzt werden
                if visible_print is True and e_match is not None:
                    angle_vals = np.array([angle_old] + [angle_new for k in range(0, num_segm)])
                else:
                    angle_vals = np.array([angle_old] + [
                        compute_angle_mixed(x_vals[k], y_vals[k], x_vals[k + 1], y_vals[k + 1], inward_cone,
                                            visible_print) for k in
                        range(0, num_segm)])
                u_vals = compute_U_values(angle_vals)
                distances_transformed = dist_transformed / num_segm * np.ones(num_segm)
                distances_bt = np.array(
                    [np.linalg.norm([x_vals[i] - x_vals[i - 1], y_vals[i] - y_vals[i - 1], z_vals[i] - z_vals[i - 1]])
                     for i in range(1, num_segm + 1)])

                # Replace new row with num_seg new rows for movements and possible command rows for the U value
                row = insert_Z(row, z_vals[0])
                row = replace_E(row, num_segm, 1)
                replacement_rows = ''
                for j in range(0, num_segm):
                    single_row = re.sub(pattern_X, 'X' + str(round(x_vals[j + 1], 3)), row)
                    single_row = re.sub(pattern_Y, 'Y' + str(round(y_vals[j + 1], 3)), single_row)
                    single_row = re.sub(pattern_Z, 'Z' + str(round(z_vals[j + 1], 3)), single_row)
                    single_row = replace_E(single_row, distances_transformed[j], distances_bt[j])
                    if np.abs(u_vals[j + 1] - u_vals[j]) <= 30:
                        single_row = insert_U(single_row, u_vals[j + 1])
                    else:
                        single_row = single_row + 'G1 E-0.800 \n' + 'G1 U' + str(u_vals[j + 1]) + ' \n' + 'G1 E0.800 \n'
                    replacement_rows = replacement_rows + single_row
                if np.amax(np.absolute(u_vals)) > 3600:
                    angle_reset = np.round(angle_vals[-1] * 360 / (2 * np.pi), 2)
                    replacement_rows = replacement_rows + 'G92 U' + str(angle_reset) + '\n'
                    angle_old = angle_new
                else:
                    angle_old = u_vals[-1] * 2 * np.pi / 360

                row = replacement_rows

                if update_x:
                    x_old = x_new
                    update_x = False
                if update_y:
                    y_old = y_new
                    update_y = False
                new_data.append(row)

    return new_data


def translate_data(data, translate_x, translate_y, z_desired, e_parallel, e_perpendicular):
    """
    Translate the GCode in x- and y-direction. Only the lines, which describe a movement will be translated.
    Additionally, if z_translation is True, the z-values will be translated such that the minimal z-value is z_desired.
    This happens by traversing the list of strings twice. If cone_type is 'inward', it is assured, that all moves
    with no extrusion have at least a height of z_desired.
    :param data: list
        List of strings, containing the GCode
    :param translate_x: float
        Float, which describes the translation in x-direction
    :param translate_y: float
        Float, which describes the translation in y-direction
    :param z_desired: float
        Desired minimal z-value
    :param e_parallel: float
        Error parallel to nozzle
    :param e_perpendicular: float
        Error perpendicular to nozzle
    :return: list
        List of strings, which contains the translated GCode
    """
    new_data = []
    pattern_X = r'X[-0-9]+[.]?[0-9]*'
    pattern_Y = r'Y[-0-9]+[.]?[0-9]*'
    pattern_Z = r'Z[-0-9]+[.]?[0-9]*'
    pattern_E = r'E[-0-9]+[.]?[0-9]*'
    pattern_U = r'U[-0-9]+[.]?[0-9]*'
    pattern_G = r'\AG[01] '
    z_initialized = False
    u_val = 0.0

    for row in data:
        g_match = re.search(pattern_G, row)
        z_match = re.search(pattern_Z, row)
        e_match = re.search(pattern_E, row)
        if g_match is not None and z_match is not None and e_match is not None:
            z_val = float(z_match.group(0).replace('Z', ''))
            if not z_initialized:
                z_min = z_val
                z_initialized = True
            if z_val < z_min:
                z_min = z_val
    z_translate = z_desired - z_min

    for row in data:

        x_match = re.search(pattern_X, row)
        y_match = re.search(pattern_Y, row)
        z_match = re.search(pattern_Z, row)
        g_match = re.search(pattern_G, row)
        u_match = re.search(pattern_U, row)

	if u_match is not None:
            u_val = np.radians(float(u_match.group(0).replace('U', '')))

        if g_match is None:
            new_data.append(row)

        else:
            if x_match is not None:
		x_val = round(float(x_match.group(0).replace('X', '')) + translate_x - (e_parallel * np.cos(u_val)) + (e_perpendicular * np.sin(u_val)), 3)	# added correction for misalignment of nozzle
                row = re.sub(pattern_X, 'X' + str(x_val), row)
            if y_match is not None:
		y_val = round(float(y_match.group(0).replace('Y', '')) + translate_y - (e_parallel * np.sin(u_val)) - (e_perpendicular * np.cos(u_val)), 3)	# added correction for misalignment of nozzle
                row = re.sub(pattern_Y, 'Y' + str(y_val), row)
            if z_match is not None:
                z_val = max(round(float(z_match.group(0).replace('Z', '')) + z_translate, 3), z_desired)
                row = re.sub(pattern_Z, 'Z' + str(z_val), row)

            new_data.append(row)

    return new_data


def backtransform_file(path, output_dir, cone_type, maximal_length, angle_comp, x_shift, y_shift, z_desired):
    """
    Read GCode from file, backtransform, translate it and save backtransformed G-Code.
    :param path: string
        String with the path to the GCode-file
    :param output_dir: string
        path of directory, where transformed STL-file will be saved
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :param maximal_length: float
        Maximal length of a segment in the original GCode
    :param angle_comp: string
        String, which describes the way, the angle is computed; one of 'radial', 'tangential', 'mixed'
    :param x_shift: float
        Float, which describes the translation in x-direction
    :param y_shift: float
        Float, which describes the translation in y-direction
    :param z_desired: float
        Desired minimal z-value
    :return: None
    """
    if angle_comp == 'radial':
        backtransform_data = backtransform_data_radial
    elif angle_comp == 'tangential':
        backtransform_data = backtransform_data_tangential
    else:
        backtransform_data = backtransform_data_mixed

    with open(path, 'r') as f_gcode:
        data = f_gcode.readlines()
    data_bt = backtransform_data(data, cone_type, maximal_length)
    data_bt_string = ''.join(data_bt)
    data_bt = [row + ' \n' for row in data_bt_string.split('\n')]
    data_bt = translate_data(data_bt, x_shift, y_shift, z_desired)
    data_bt_string = ''.join(data_bt)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    file_name = path[path.rfind('/'):]
    file_name = file_name.replace('.gcode', '_bt_' + cone_type + '_' + angle_comp + '.gcode')
    output_path = output_dir + file_name
    with open(output_path, 'w+') as f_gcode_bt:
        f_gcode_bt.write(data_bt_string)

    end = time.time()
    print('GCode generated in {:.1f}s, saved in {}'.format(end - start, output_path))
    return None


# -------------------------------------------------------------------------------
# Apply the functions for a G-Code file
# -------------------------------------------------------------------------------

# G-Code backtransformation function parameters
file_path = '/home/maurus/ownCloud/Private/VT_3DDrucker/Code_old/G_Codes/Wuerfel_klein_transformiert.gcode'
dir_backtransformed = '/home/maurus/ownCloud/Private/VT_3DDrucker/Code_old/G_Codes_Backtransformed/'
transformation_type = 'inward'  # inward or outward
angle_type = 'radial'  # radial or tangential
max_length = 5  # maximal length of a segment in mm
x_shift = 0     # shift of code in x-direction
y_shift = 0     # shift of code in x-direction
z_desired = 0.3     # desired height in z-direction

# G-Code backtransformation function call
backtransform_file(path=file_path,
                   output_dir=dir_backtransformed,
                   cone_type=transformation_type,
                   maximal_length=max_length,
                   angle_comp=angle_type,
                   x_shift=x_shift,
                   y_shift=y_shift,
                   z_desired=z_desired
                   )
