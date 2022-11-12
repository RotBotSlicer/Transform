import re
import numpy as np
import time

# -----------------------------------------------------------------------------------------
# Transformation Settings
# -----------------------------------------------------------------------------------------
FILE_NAME = 'tower_01_B.gcode'      # filename including extension
FOLDER_NAME = 'gcodes/'                              # name of the subfolder in which the gcode is located
CONE_ANGLE = 16                                      # transformation angle
CONE_TYPE = 'outward'                                # type of the cone: 'inward' & 'outward'
FIRST_LAYER_HEIGHT = 0.2                            # moves all the gcode up to this height. Use also for stacking
X_SHIFT = 110                                       # moves your gcode away from the origin into the center of the bed (usually bed size / 2)
Y_SHIFT = 90


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
    pattern_X = r'X[-0-9]*[.]?[0-9]*'
    pattern_Y = r'Y[-0-9]*[.]?[0-9]*'
    pattern_Z = r'Z[-0-9]*[.]?[0-9]*'
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
    the factor is obtained by the ratio of new distance to old distance. (wuem: Due to the transformation, the amount has to be
    divided by sqrt(2). replace_E is accessed 2 times.)
    :param row: string
        String containing the row, of which the extruder value should be replaced
    :param dist_old: float
        Length of the distance before backtransformation
    :param dist_new: float
        Length of the distance after backtransformation
    :param corr_value: float
        additional correction value due to transformation
    :return: string
        New string, containing the row with replaced extruder value
    """
    pattern_E = r'E[-0-9]*[.]?[0-9]*'
    match_e = re.search(pattern_E, row)
    if match_e is None:
        return row
    e_val_old = float(match_e.group(0).replace('E', ''))
    if dist_old == 0:
        e_val_new = 0
    else:
        e_val_new = e_val_old * dist_new * corr_value / dist_old
    e_str_new = 'E' + f'{e_val_new:.5f}'
    row_new = row[0:match_e.start(0)] + e_str_new + row[match_e.end(0):]
    return row_new


def compute_angle_radial(x_old, y_old, x_new, y_new, inward_cone):
    """
    Compute the angle of the printing head, when moving from an old point [x_old, y_old] to a new point [x_new, y_new].
    (Note: the z-value is not considered for the orientation of the printing head.) The direction is given by the
    direction of the new point by the arctan2 value according to the coordinates.
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
    angle = np.arctan2(y_new, x_new)
    if inward_cone:
        angle = angle + np.pi
    return angle





def compute_U_values(angle_array):
    """
    Compute the U-values, which will be inserted, according to given angle values.
    The U-values are computed such that there are no discontinuous jumps from pi to -pi.
    :param angle_array: array
        Array, which contains the angle values in radian
    :return array
        Array, which contains U-values in degrees
    """
    # angle_candidates = np.around(np.array([angle_array, angle_array - 2 * np.pi, angle_array + 2 * np.pi]).T, 4)
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
    pattern_Z = r'Z[-0-9]*[.]?[0-9]*'
    match_z = re.search(pattern_Z, row)
    pattern_U = r'U[-0-9]*[.]?[0-9]*'
    match_u = re.search(pattern_U, row)

    if match_u is None:
        row_new = row[0:match_z.end(0)] + ' U' + str(angle) + row[match_z.end(0):]
    else:
        row_new = re.sub(pattern_U, 'U' + str(angle), row)

    return row_new


def backtransform_data_radial(data, cone_type, maximal_length, cone_angle_rad):
    """
    Backtransform GCode, which is given in a list, each element describing a row. Rows which describe a movement
    are detected, x-, y-, z-, E- and U-values are replaced accordingly to the transformation. If a original segment
    is too long, it gets divided into sub-segments before the backtransformation. The U-values are computed
    using the funciton compute_angle_radial.(wuem: added, that while travel moves, nozzle only rises 1 mm above highest
    printed point and not along cone)
    :param data: list
        List of strings, describing each line of the GCode, which is to be backtransformed
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :param maximal_length: float
        Maximal length of a segment in the original GCode; every longer segment is divided, such that the resulting
        segments are shorter than maximal_length
    : param cone_angle_rad
        Angle of transformation cone in rad
    :return: list
        List of strings, which describe the new GCode.
    """
    new_data = []
    pattern_X = r'X[-0-9]*[.]?[0-9]*'
    pattern_Y = r'Y[-0-9]*[.]?[0-9]*'
    pattern_Z = r'Z[-0-9]*[.]?[0-9]*'
    pattern_E = r'E[-0-9]*[.]?[0-9]*'
    pattern_G = r'\AG[1] '

    x_old, y_old = 0, 0
    x_new, y_new = 0, 0
    z_layer = 0
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

                # Compute new distance and angle according to new row
                e_match = re.search(pattern_E, row)
                x_old_bt, x_new_bt = x_old * np.cos(cone_angle_rad), x_new * np.cos(cone_angle_rad)
                y_old_bt, y_new_bt = y_old * np.cos(cone_angle_rad), y_new * np.cos(cone_angle_rad)
                dist_transformed = np.linalg.norm([x_new - x_old, y_new - y_old])

                # Compute new values for backtransformation of row
                num_segm = int(dist_transformed // maximal_length + 1)
                x_vals = np.linspace(x_old_bt, x_new_bt, num_segm + 1)
                y_vals = np.linspace(y_old_bt, y_new_bt, num_segm + 1)
                if inward_cone and e_match is None and (update_x or update_y):
                    z_start = z_layer + c * np.sqrt(x_old_bt ** 2 + y_old_bt ** 2) * np.tan(cone_angle_rad)
                    z_end = z_layer + c * np.sqrt(x_new_bt ** 2 + y_new_bt ** 2) * np.tan(cone_angle_rad)
                    z_vals = np.linspace(z_start, z_end, num_segm + 1)
                else:
                    z_vals = np.array([z_layer + c * np.sqrt(x ** 2 + y ** 2) * np.tan(cone_angle_rad) for x, y in zip(x_vals, y_vals)])
                    if e_match and (np.max(z_vals) > z_max or z_max == 0):
                        z_max = np.max(z_vals) # save hightes point with material extruded
                    if e_match is None and np.max(z_vals) > z_max:
                        np.minimum(z_vals, (z_max + 1), z_vals) # cut away all travel moves, that are higher than max height extruded + 1 mm safety
                        # das hier könnte noch verschönert werden, in dem dann eine alle abgeschnittenen Werte mit einer einer geraden Linie ersetzt werden

                distances_transformed = dist_transformed / num_segm * np.ones(num_segm)
                distances_bt = np.array(
                    [np.linalg.norm([x_vals[i] - x_vals[i - 1], y_vals[i] - y_vals[i - 1], z_vals[i] - z_vals[i - 1]])
                     for i in range(1, num_segm + 1)])

                # Replace new row with num_seg new rows for movements and possible command rows for the U value
                row = insert_Z(row, z_vals[0])
                row = replace_E(row, num_segm, 1, 1 * np.cos(cone_angle_rad))
                replacement_rows = ''
                for j in range(0, num_segm):
                    single_row = re.sub(pattern_X, 'X' + str(round(x_vals[j + 1], 3)), row)
                    single_row = re.sub(pattern_Y, 'Y' + str(round(y_vals[j + 1], 3)), single_row)
                    single_row = re.sub(pattern_Z, 'Z' + str(round(z_vals[j + 1], 3)), single_row)
                    single_row = replace_E(single_row, distances_transformed[j], distances_bt[j], 1)
                    replacement_rows = replacement_rows + single_row
                row = replacement_rows

                if update_x:
                    x_old = x_new
                    update_x = False
                if update_y:
                    y_old = y_new
                    update_y = False

                new_data.append(row)

    return new_data



def translate_data(data, cone_type, translate_x, translate_y, z_desired, e_parallel, e_perpendicular):
    """
    Translate the GCode in x- and y-direction. Only the lines, which describe a movement will be translated.
    Additionally, if z_translation is True, the z-values will be translated such that the minimal z-value is z_desired.
    This happens by traversing the list of strings twice. If cone_type is 'inward', it is assured, that all moves
    with no extrusion have at least a hight of z_desired.
    :param data: list
        List of strings, containing the GCode
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
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
    pattern_X = r'X[-0-9]*[.]?[0-9]*'
    pattern_Y = r'Y[-0-9]*[.]?[0-9]*'
    pattern_Z = r'Z[-0-9]*[.]?[0-9]*'
    pattern_E = r'E[-0-9]*[.]?[0-9]*'
    pattern_G = r'\AG[1] '
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

        if g_match is None:
            new_data.append(row)

        else:
            if x_match is not None:
                x_val = round(float(x_match.group(0).replace('X', '')) + translate_x - (e_parallel * np.cos(u_val)) + (e_perpendicular * np.sin(u_val)), 3)
                row = re.sub(pattern_X, 'X' + str(x_val), row)
            if y_match is not None:
                y_val = round(float(y_match.group(0).replace('Y', '')) + translate_y - (e_parallel * np.sin(u_val)) - (e_perpendicular * np.cos(u_val)), 3)
                row = re.sub(pattern_Y, 'Y' + str(y_val), row)
            if z_match is not None:
                z_val = max(round(float(z_match.group(0).replace('Z', '')) + z_translate, 3), z_desired)
                row = re.sub(pattern_Z, 'Z' + str(z_val), row)

            new_data.append(row)

    return new_data


def backtransform_file(path, cone_type, maximal_length, angle_comp, x_shift, y_shift, cone_angle_deg, z_desired, e_parallel, e_perpendicular):
    """
    Read GCode from file, backtransform and translate it.
    :param path: string
        String with the path to the GCode-file
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
    :param cone_angle_deg: int
        Angle of transformation cone in degrees
    :param z_desired: float
        Desired minimal z-value
    :param e_parallel: float
        Error parallel to nozzle
    :param e_perpendicular: float
        Error perpendicular to nozzle
    :return: None
    """
    
    cone_angle_rad = cone_angle_deg / 180 * np.pi

    if angle_comp == 'radial':
        backtransform_data = backtransform_data_radial

    with open(path, 'r') as f_gcode:
        data = f_gcode.readlines()
    data_bt = backtransform_data(data, cone_type, maximal_length, cone_angle_rad)
    data_bt_string = ''.join(data_bt)
    data_bt = [row + ' \n' for row in data_bt_string.split('\n')]
    data_bt = translate_data(data_bt, cone_type, x_shift, y_shift, z_desired, e_parallel, e_perpendicular)
    data_bt_string = ''.join(data_bt)

    path_write = re.sub(r'gcodes', 'gcodes_backtransformed', path)
    path_write = re.sub(r'.gcode', '_bt_' + cone_type + '_' + angle_comp + '.gcode', path_write)
    print(path_write)
    with open(path_write, 'w+') as f_gcode_bt:
        f_gcode_bt.write(data_bt_string)
    print('File successfully backtransformed and translated.')

    return None

starttime = time.time()
backtransform_file(path=FOLDER_NAME + FILE_NAME, cone_type=CONE_TYPE, maximal_length=0.5, angle_comp='radial', x_shift=X_SHIFT, y_shift=Y_SHIFT,
                   cone_angle_deg=CONE_ANGLE, z_desired=FIRST_LAYER_HEIGHT, e_parallel=0, e_perpendicular=0)
endtime = time.time()
print('GCode translated, time used:', endtime - starttime)