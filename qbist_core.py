import random
import math
from enum import Enum
import struct
import numpy as np

# Optional Numba acceleration
try:
    import numba as _numba
    from numba import njit, prange
    NUMBA_AVAILABLE = True
except Exception:
    NUMBA_AVAILABLE = False

'''
This module contains the core logic for the Qbist pattern generation and manipulation.
It defines the data structures and algorithms for creating, modifying, optimizing, and calculating the colors of Qbist patterns based on a sequence of transformations.

The main components include:
- TransformType: An enumeration of the different transformation types that can be applied to color registers.
- ExpInfo: A class that holds all the information defining a Qbist pattern, including the sequence of transformations and the registers they operate on.
- create_info: A function to generate a new ExpInfo object with randomly initialized transformation parameters.
- modify_info: A function to create a new ExpInfo object by making random modifications to an existing one.
- optimize_info: A function to analyze an ExpInfo object and mark which transformations and registers are actually necessary for computing the final output, allowing for optimization during color calculation.
- calculate_pixel_color: A function to compute the RGB color for a single point based on the ExpInfo and its transformations.
- generate_image_data: A function to generate the raw pixel data for an image based on the ExpInfo, supporting oversampling for anti-aliasing.
- load_qbe_data and save_qbe_data: Functions to load and save Qbist pattern data from/to .qbe files, which are raw binary dumps of the transformation parameters.   

'''

# Maximum number of transformation steps in a Qbist pattern.
MAX_TRANSFORMS = 36
# Number of color registers available for transformations.
NUM_REGISTERS = 6


class TransformType(Enum):
    """
    Enumeration of the different types of transformations that can be applied
    to color registers in the Qbist algorithm.
    """
    PROJECTION = 0
    SHIFT = 1
    SHIFTBACK = 2
    ROTATE = 3
    ROTATE2 = 4
    MULTIPLY = 5
    SINE = 6
    CONDITIONAL = 7
    COMPLEMENT = 8

# Total number of distinct transformation types defined in the TransformType enum.
NUM_TRANSFORM_TYPES = len(TransformType)

class ExpInfo:
    """
    Holds all the information defining a Qbist pattern.
    This includes the sequence of transformations and the registers they operate on.
    """
    def __init__(self):
        self.transform_sequence = [TransformType.PROJECTION] * MAX_TRANSFORMS
        self.source = [0] * MAX_TRANSFORMS
        self.control = [0] * MAX_TRANSFORMS
        self.dest = [0] * MAX_TRANSFORMS
        self.used_trans_flag = [False] * MAX_TRANSFORMS
        self.used_reg_flag = [False] * NUM_REGISTERS

    def copy(self):
        """
        Creates a shallow copy of this ExpInfo object.
        The optimization flags (used_trans_flag, used_reg_flag) are not copied
        as they are typically recalculated.
        """
        new_info = ExpInfo()
        new_info.transform_sequence = list(self.transform_sequence)
        new_info.source = list(self.source)
        new_info.control = list(self.control)
        new_info.dest = list(self.dest)
        # Optimization flags are recalculated, not copied by default
        return new_info

    def __eq__(self, other):
        """
        Compares two ExpInfo objects for equality based on their transformation parameters.
        """
        if not isinstance(other, ExpInfo):
            return NotImplemented
        return (self.transform_sequence == other.transform_sequence and
                self.source == other.source and
                self.control == other.control and
                self.dest == other.dest)


def create_info():
    """
    Creates a new ExpInfo object with randomly initialized transformation parameters.
    This is used to generate a new base Qbist pattern.
    """
    info = ExpInfo()
    used_dests = set()
    for k in range(MAX_TRANSFORMS):
        # Vermeide, dass alle dest gleich sind
        dest = random.randrange(NUM_REGISTERS)
        while dest in used_dests and len(used_dests) < NUM_REGISTERS:
            dest = random.randrange(NUM_REGISTERS)
        used_dests.add(dest)
        info.dest[k] = dest

        # Vermeide, dass alle Transformationen gleich sind
        if k < 3:
            info.transform_sequence[k] = random.choice([t for t in TransformType if t != TransformType.PROJECTION])
        else:
            info.transform_sequence[k] = random.choice(list(TransformType))
        info.source[k] = random.randrange(NUM_REGISTERS)
        info.control[k] = random.randrange(NUM_REGISTERS)
    return info

def modify_info(original_info: ExpInfo):
    """
    Creates a new ExpInfo object by making a random number of modifications
    to an existing (original) ExpInfo object.
    This is used to generate variations of a pattern.

    Args:
        original_info: The ExpInfo object to base the modifications on.
    """
    new_info = original_info.copy()
    num_modifications = random.randrange(MAX_TRANSFORMS)
    for _ in range(num_modifications):
        idx_to_modify = random.randrange(MAX_TRANSFORMS)
        modification_type = random.randrange(4)
        if modification_type == 0:
            new_info.transform_sequence[idx_to_modify] = random.choice(list(TransformType))
        elif modification_type == 1:
            new_info.source[idx_to_modify] = random.randrange(NUM_REGISTERS)
        elif modification_type == 2:
            new_info.control[idx_to_modify] = random.randrange(NUM_REGISTERS)
        else:  # 3
            new_info.dest[idx_to_modify] = random.randrange(NUM_REGISTERS)
    return new_info

def _check_last_modified_recursive(exp_info: ExpInfo,
                                   transform_idx_upper_search_limit: int,
                                   target_register_n: int):
    """
    Recursively determines which transformations and initial registers are actually
    used to compute the final color (which depends on register 0).
    This is a helper function for `optimize_info`.

    Args:
        exp_info: The ExpInfo object to analyze.
        transform_idx_upper_search_limit: The upper index in the transform sequence to search.
        target_register_n: The register index whose usage is being traced back.
    """
    p = transform_idx_upper_search_limit - 1
    while p >= 0:
        # Ensure dest index is valid before comparing
        if 0 <= exp_info.dest[p] < NUM_REGISTERS and exp_info.dest[p] == target_register_n:
            break
        p -= 1
    
    if p < 0:
        # If no transformation writes to target_register_n, it means this register
        # is an initial input (like x, y, or i coordinates).
        if 0 <= target_register_n < NUM_REGISTERS:
            exp_info.used_reg_flag[target_register_n] = True
    else:
        if not exp_info.used_trans_flag[p]:
            exp_info.used_trans_flag[p] = True
            if 0 <= exp_info.source[p] < NUM_REGISTERS:
                 _check_last_modified_recursive(exp_info, p, exp_info.source[p])
            if 0 <= exp_info.control[p] < NUM_REGISTERS:
                 _check_last_modified_recursive(exp_info, p, exp_info.control[p])

def optimize_info(info: ExpInfo):
    """
    Analyzes the ExpInfo object to mark which transformations and initial registers
    are actually necessary to calculate the final output (which depends on register 0).
    Unused transformations can then be skipped during pixel color calculation.
    It also standardizes the control register for certain transform types.

    Args:
        info: The ExpInfo object to be optimized.
    """
    info.used_trans_flag = [False] * MAX_TRANSFORMS
    info.used_reg_flag = [False] * NUM_REGISTERS
    for i in range(MAX_TRANSFORMS):
        tt = info.transform_sequence[i]
        if tt == TransformType.ROTATE or \
           tt == TransformType.ROTATE2 or \
           tt == TransformType.COMPLEMENT:
            if 0 <= info.dest[i] < NUM_REGISTERS: # Ensure dest is valid before assigning
                info.control[i] = info.dest[i]
            
    # Start the recursive check from the final output register (register 0)
    if 0 <= 0 < NUM_REGISTERS: # Ensure register 0 is a valid index
        _check_last_modified_recursive(info, MAX_TRANSFORMS, 0)


def calculate_pixel_color(info: ExpInfo, abs_x_oversampled: int, abs_y_oversampled: int,
                          total_width_oversampled: int, total_height_oversampled: int):
    """
    Calculates the RGB color for a single point (pixel or sub-pixel for oversampling)
    based on the provided ExpInfo and coordinates.

    Args:
        info: The ExpInfo object defining the Qbist pattern.
        abs_x_oversampled: The absolute x-coordinate of the point (can be sub-pixel).
        abs_y_oversampled: The absolute y-coordinate of the point (can be sub-pixel).
        total_width_oversampled: The total width of the image in oversampled units.
        total_height_oversampled: The total height of the image in oversampled units.

    Returns:
        A tuple (r, g, b) of float values between 0.0 and 1.0.
    """
    reg = [[0.0, 0.0, 0.0] for _ in range(NUM_REGISTERS)]

    # Pre-calculate inverses for division
    inv_total_width_os = 1.0 / total_width_oversampled if total_width_oversampled > 0 else 0.0
    inv_total_height_os = 1.0 / total_height_oversampled if total_height_oversampled > 0 else 0.0
    inv_num_registers = 1.0 / NUM_REGISTERS if NUM_REGISTERS > 0 else 0.0
    # Cast to float once
    f_abs_x_oversampled = float(abs_x_oversampled)
    f_abs_y_oversampled = float(abs_y_oversampled)

    for i in range(NUM_REGISTERS):
        if info.used_reg_flag[i]:
            reg[i][0] = f_abs_x_oversampled * inv_total_width_os
            reg[i][1] = f_abs_y_oversampled * inv_total_height_os
            reg[i][2] = float(i) * inv_num_registers
        else:
            # If a register is not marked as used by optimize_info, initialize to zero.
            reg[i][0], reg[i][1], reg[i][2] = 0.0, 0.0, 0.0

    for i in range(MAX_TRANSFORMS):
        if info.used_trans_flag[i]:
            # Use local variables for frequently accessed attributes
            transform_type = info.transform_sequence[i]
            sr_idx = info.source[i]
            cr_idx = info.control[i]
            dr_idx = info.dest[i]

            # Basic bounds check for safety, though values should be constrained by generation
            if not (0 <= sr_idx < NUM_REGISTERS and \
                    0 <= cr_idx < NUM_REGISTERS and \
                    0 <= dr_idx < NUM_REGISTERS):
                continue 
            
            sr, cr = reg[sr_idx], reg[cr_idx]
            
            # Temporary variables for destination register values
            # This avoids modifying reg[dr_idx] directly if it's also sr or cr in the same step.
            dest_val0, dest_val1, dest_val2 = 0.0, 0.0, 0.0
            
            if transform_type == TransformType.PROJECTION:
                scalar_prod = (sr[0] * cr[0]) + (sr[1] * cr[1]) + (sr[2] * cr[2])
                dest_val0 = scalar_prod * sr[0]
                dest_val1 = scalar_prod * sr[1]
                dest_val2 = scalar_prod * sr[2]
            elif transform_type == TransformType.SHIFT:
                dest_val0 = sr[0] + cr[0]
                if dest_val0 >= 1.0: dest_val0 -= 1.0
                dest_val1 = sr[1] + cr[1]
                if dest_val1 >= 1.0: dest_val1 -= 1.0
                dest_val2 = sr[2] + cr[2]
                if dest_val2 >= 1.0: dest_val2 -= 1.0
            elif transform_type == TransformType.SHIFTBACK:
                dest_val0 = sr[0] - cr[0]
                if dest_val0 <= 0.0: dest_val0 += 1.0
                dest_val1 = sr[1] - cr[1]
                if dest_val1 <= 0.0: dest_val1 += 1.0
                dest_val2 = sr[2] - cr[2]
                if dest_val2 <= 0.0: dest_val2 += 1.0
            elif transform_type == TransformType.ROTATE:
                dest_val0, dest_val1, dest_val2 = sr[1], sr[2], sr[0]
            elif transform_type == TransformType.ROTATE2:
                dest_val0, dest_val1, dest_val2 = sr[2], sr[0], sr[1]
            elif transform_type == TransformType.MULTIPLY:
                dest_val0 = sr[0] * cr[0]
                dest_val1 = sr[1] * cr[1]
                dest_val2 = sr[2] * cr[2]
            elif transform_type == TransformType.SINE:
                dest_val0 = 0.5 + (0.5 * math.sin(20.0 * sr[0] * cr[0]))
                dest_val1 = 0.5 + (0.5 * math.sin(20.0 * sr[1] * cr[1]))
                dest_val2 = 0.5 + (0.5 * math.sin(20.0 * sr[2] * cr[2]))
            elif transform_type == TransformType.CONDITIONAL:
                if (cr[0] + cr[1] + cr[2]) > 0.5:
                    dest_val0, dest_val1, dest_val2 = sr[0], sr[1], sr[2]
                else:
                    dest_val0, dest_val1, dest_val2 = cr[0], cr[1], cr[2]
            elif transform_type == TransformType.COMPLEMENT:
                dest_val0 = 1.0 - sr[0]
                dest_val1 = 1.0 - sr[1]
                dest_val2 = 1.0 - sr[2]
            
            # Nach der Berechnung der Zielwerte:
            # Clamp und prüfe auf NaN/Inf
            dest_val0 = min(1.0, max(0.0, dest_val0 if math.isfinite(dest_val0) else 0.0))
            dest_val1 = min(1.0, max(0.0, dest_val1 if math.isfinite(dest_val1) else 0.0))
            dest_val2 = min(1.0, max(0.0, dest_val2 if math.isfinite(dest_val2) else 0.0))

            reg[dr_idx][0] = dest_val0
            reg[dr_idx][1] = dest_val1
            reg[dr_idx][2] = dest_val2
    
    # The final color is taken from register 0.
    r, g, b = reg[0][0], reg[0][1], reg[0][2]
    r = min(1.0, max(0.0, r if math.isfinite(r) else 0.0))
    g = min(1.0, max(0.0, g if math.isfinite(g) else 0.0))
    b = min(1.0, max(0.0, b if math.isfinite(b) else 0.0))

    return r, g, b


def _expinfo_to_arrays(info: ExpInfo):
    """Convert an ExpInfo into primitive numpy arrays suitable for Numba.

    Returns:
        transform_seq, source, control, dest, used_trans_flag, used_reg_flag
    """
    transform_seq = np.empty(MAX_TRANSFORMS, dtype=np.int64)
    source = np.empty(MAX_TRANSFORMS, dtype=np.int64)
    control = np.empty(MAX_TRANSFORMS, dtype=np.int64)
    dest = np.empty(MAX_TRANSFORMS, dtype=np.int64)
    used_trans_flag = np.empty(MAX_TRANSFORMS, dtype=np.bool_)
    used_reg_flag = np.empty(NUM_REGISTERS, dtype=np.bool_)

    for i in range(MAX_TRANSFORMS):
        transform_seq[i] = int(info.transform_sequence[i].value)
        source[i] = int(info.source[i])
        control[i] = int(info.control[i])
        dest[i] = int(info.dest[i])
        used_trans_flag[i] = bool(info.used_trans_flag[i])
    for i in range(NUM_REGISTERS):
        used_reg_flag[i] = bool(info.used_reg_flag[i])

    return transform_seq, source, control, dest, used_trans_flag, used_reg_flag


if NUMBA_AVAILABLE:
    from numba import njit

    @njit(fastmath=True)
    def _calculate_pixel_color_numba(transform_seq, source, control, dest, used_trans_flag, used_reg_flag,
                                     abs_x_oversampled, abs_y_oversampled, total_width_oversampled, total_height_oversampled):
        reg = np.zeros((NUM_REGISTERS, 3), dtype=np.float64)

        inv_total_width_os = 1.0 / total_width_oversampled if total_width_oversampled > 0 else 0.0
        inv_total_height_os = 1.0 / total_height_oversampled if total_height_oversampled > 0 else 0.0
        inv_num_registers = 1.0 / NUM_REGISTERS if NUM_REGISTERS > 0 else 0.0

        f_abs_x_oversampled = float(abs_x_oversampled)
        f_abs_y_oversampled = float(abs_y_oversampled)

        for i in range(NUM_REGISTERS):
            if used_reg_flag[i]:
                reg[i, 0] = f_abs_x_oversampled * inv_total_width_os
                reg[i, 1] = f_abs_y_oversampled * inv_total_height_os
                reg[i, 2] = float(i) * inv_num_registers
            else:
                reg[i, 0] = 0.0
                reg[i, 1] = 0.0
                reg[i, 2] = 0.0

        for i in range(MAX_TRANSFORMS):
            if not used_trans_flag[i]:
                continue
            tt = transform_seq[i]
            sr_idx = source[i]
            cr_idx = control[i]
            dr_idx = dest[i]

            if not (0 <= sr_idx < NUM_REGISTERS and 0 <= cr_idx < NUM_REGISTERS and 0 <= dr_idx < NUM_REGISTERS):
                continue

            sr0 = reg[sr_idx, 0]
            sr1 = reg[sr_idx, 1]
            sr2 = reg[sr_idx, 2]
            cr0 = reg[cr_idx, 0]
            cr1 = reg[cr_idx, 1]
            cr2 = reg[cr_idx, 2]

            dest_val0 = 0.0
            dest_val1 = 0.0
            dest_val2 = 0.0

            if tt == 0:  # PROJECTION
                scalar_prod = (sr0 * cr0) + (sr1 * cr1) + (sr2 * cr2)
                dest_val0 = scalar_prod * sr0
                dest_val1 = scalar_prod * sr1
                dest_val2 = scalar_prod * sr2
            elif tt == 1:  # SHIFT
                dest_val0 = sr0 + cr0
                if dest_val0 >= 1.0:
                    dest_val0 -= 1.0
                dest_val1 = sr1 + cr1
                if dest_val1 >= 1.0:
                    dest_val1 -= 1.0
                dest_val2 = sr2 + cr2
                if dest_val2 >= 1.0:
                    dest_val2 -= 1.0
            elif tt == 2:  # SHIFTBACK
                dest_val0 = sr0 - cr0
                if dest_val0 <= 0.0:
                    dest_val0 += 1.0
                dest_val1 = sr1 - cr1
                if dest_val1 <= 0.0:
                    dest_val1 += 1.0
                dest_val2 = sr2 - cr2
                if dest_val2 <= 0.0:
                    dest_val2 += 1.0
            elif tt == 3:  # ROTATE
                dest_val0 = sr1
                dest_val1 = sr2
                dest_val2 = sr0
            elif tt == 4:  # ROTATE2
                dest_val0 = sr2
                dest_val1 = sr0
                dest_val2 = sr1
            elif tt == 5:  # MULTIPLY
                dest_val0 = sr0 * cr0
                dest_val1 = sr1 * cr1
                dest_val2 = sr2 * cr2
            elif tt == 6:  # SINE
                dest_val0 = 0.5 + (0.5 * math.sin(20.0 * sr0 * cr0))
                dest_val1 = 0.5 + (0.5 * math.sin(20.0 * sr1 * cr1))
                dest_val2 = 0.5 + (0.5 * math.sin(20.0 * sr2 * cr2))
            elif tt == 7:  # CONDITIONAL
                if (cr0 + cr1 + cr2) > 0.5:
                    dest_val0 = sr0
                    dest_val1 = sr1
                    dest_val2 = sr2
                else:
                    dest_val0 = cr0
                    dest_val1 = cr1
                    dest_val2 = cr2
            elif tt == 8:  # COMPLEMENT
                dest_val0 = 1.0 - sr0
                dest_val1 = 1.0 - sr1
                dest_val2 = 1.0 - sr2

            # Clamp
            if not np.isfinite(dest_val0):
                dest_val0 = 0.0
            if not np.isfinite(dest_val1):
                dest_val1 = 0.0
            if not np.isfinite(dest_val2):
                dest_val2 = 0.0

            if dest_val0 < 0.0:
                dest_val0 = 0.0
            elif dest_val0 > 1.0:
                dest_val0 = 1.0
            if dest_val1 < 0.0:
                dest_val1 = 0.0
            elif dest_val1 > 1.0:
                dest_val1 = 1.0
            if dest_val2 < 0.0:
                dest_val2 = 0.0
            elif dest_val2 > 1.0:
                dest_val2 = 1.0

            reg[dr_idx, 0] = dest_val0
            reg[dr_idx, 1] = dest_val1
            reg[dr_idx, 2] = dest_val2

        r = reg[0, 0]
        g = reg[0, 1]
        b = reg[0, 2]

        if not np.isfinite(r):
            r = 0.0
        if not np.isfinite(g):
            g = 0.0
        if not np.isfinite(b):
            b = 0.0

        if r < 0.0:
            r = 0.0
        elif r > 1.0:
            r = 1.0
        if g < 0.0:
            g = 0.0
        elif g > 1.0:
            g = 1.0
        if b < 0.0:
            b = 0.0
        elif b > 1.0:
            b = 1.0

        return r, g, b

    @njit(parallel=True, fastmath=True)
    def _generate_image_data_numba(transform_seq, source, control, dest, used_trans_flag, used_reg_flag,
                                   img_width, img_height, oversampling, max_attempts):
        # Note: optimize_info should be called before converting to arrays in Python
        total_w_os = img_width * oversampling
        total_h_os = img_height * oversampling
        num_samples = oversampling * oversampling

        out = np.empty((img_height, img_width, 4), dtype=np.uint8)

        # Parallelize over rows
        for y_px in prange(img_height):
            for x_px in range(img_width):
                accum_r = 0.0
                accum_g = 0.0
                accum_b = 0.0
                for yy_os in range(oversampling):
                    for xx_os in range(oversampling):
                        abs_x_os = x_px * oversampling + xx_os
                        abs_y_os = y_px * oversampling + yy_os
                        r, g, b = _calculate_pixel_color_numba(transform_seq, source, control, dest, used_trans_flag, used_reg_flag,
                                                               abs_x_os, abs_y_os, total_w_os, total_h_os)
                        accum_r += r
                        accum_g += g
                        accum_b += b
                inv_num_samples = 1.0 / float(num_samples) if num_samples != 0 else 1.0
                final_r = accum_r * inv_num_samples
                final_g = accum_g * inv_num_samples
                final_b = accum_b * inv_num_samples

                r_byte = int(max(0, min(255, int(final_r * 255.999))))
                g_byte = int(max(0, min(255, int(final_g * 255.999))))
                b_byte = int(max(0, min(255, int(final_b * 255.999))))

                out[y_px, x_px, 0] = r_byte
                out[y_px, x_px, 1] = g_byte
                out[y_px, x_px, 2] = b_byte
                out[y_px, x_px, 3] = 255

        return out.reshape((-1,)).copy()

def generate_image_data(info: ExpInfo, img_width: int, img_height: int, oversampling: int = 1, max_attempts=5):
    """
    Generates the raw pixel data for an image based on the ExpInfo.
    Supports oversampling for anti-aliasing.

    Args:
        info: The ExpInfo object defining the Qbist pattern.
        img_width: The desired width of the final image in pixels.
        img_height: The desired height of the final image in pixels.
        oversampling: The oversampling factor (e.g., 1 for no oversampling,
                      2 for 2x2=4 samples per pixel, 4 for 4x4=16 samples per pixel).
        max_attempts: The maximum number of attempts to generate a non-monochrome image.

    Returns:
        A bytes object containing the RGBA pixel data (4 bytes per pixel).
    """
    # If Numba is available, use the jitted implementation for the heavy loops.
    if NUMBA_AVAILABLE:
        last_bytes = None
        for attempt in range(max_attempts):
            optimize_info(info)
            transform_seq, source, control, dest, used_trans_flag, used_reg_flag = _expinfo_to_arrays(info)
            raw_flat = _generate_image_data_numba(transform_seq, source, control, dest, used_trans_flag, used_reg_flag,
                                                  img_width, img_height, oversampling, 1)
            # _generate_image_data_numba returns a flat 1D uint8 array
            pixel_bytes = bytes(raw_flat.tobytes()) if hasattr(raw_flat, 'tobytes') else bytes(np.asarray(raw_flat).tobytes())
            last_bytes = pixel_bytes
            if not is_image_monochrome(pixel_bytes, img_width, img_height):
                return pixel_bytes
            info = create_info()
        return last_bytes if last_bytes is not None else bytes(bytearray(img_width * img_height * 4))

    # Fallback: original pure-Python implementation
    for attempt in range(max_attempts):
        optimize_info(info)
        pixel_data = bytearray(img_width * img_height * 4)
        
        total_width_oversampled = img_width * oversampling
        total_height_oversampled = img_height * oversampling
        # Pre-calculate inverse of num_samples for oversampling
        num_samples_float = float(oversampling * oversampling)
        if num_samples_float == 0: # Should not happen if oversampling >= 1
            inv_num_samples = 1.0
        else:
            inv_num_samples = 1.0 / num_samples_float

        for y_px in range(img_height):
            for x_px in range(img_width):
                accum_r, accum_g, accum_b = 0.0, 0.0, 0.0
                # Oversampling loop: calculate color for multiple sub-pixels
                for yy_os in range(oversampling):
                    for xx_os in range(oversampling):
                        abs_x_os = x_px * oversampling + xx_os
                        abs_y_os = y_px * oversampling + yy_os
                        
                        r, g, b = calculate_pixel_color(info, abs_x_os, abs_y_os, 
                                                        total_width_oversampled, total_height_oversampled)
                        accum_r += r
                        accum_g += g
                        accum_b += b
                # Average the accumulated sub-pixel colors
                final_r = accum_r * inv_num_samples
                final_g = accum_g * inv_num_samples
                final_b = accum_b * inv_num_samples

                # Convert float (0.0-1.0) to byte (0-255)
                r_byte = max(0, min(255, int(final_r * 255.999))) # Use 255.999 for better rounding to 255
                g_byte = max(0, min(255, int(final_g * 255.999)))
                b_byte = max(0, min(255, int(final_b * 255.999)))
                
                idx = (y_px * img_width + x_px) * 4
                pixel_data[idx] = r_byte
                pixel_data[idx+1] = g_byte
                pixel_data[idx+2] = b_byte
                pixel_data[idx+3] = 255 # Alpha
            
        if not is_image_monochrome(pixel_data, img_width, img_height):
            return bytes(pixel_data)
        info = create_info()  # Neues Pattern
    return bytes(pixel_data)  # Letzter Versuch, auch wenn einfarbig

def load_qbe_data(filepath: str):
    """
    Loads Qbist pattern data from a .qbe file into an ExpInfo object.
    The .qbe file format is a raw binary dump of the transformation parameters.

    Args:
        filepath: The path to the .qbe file.

    Returns:
        An ExpInfo object if successful, None otherwise.
    """
    info = ExpInfo()
    try:
        with open(filepath, "rb") as f:
            buf = f.read(288)
            if len(buf) != 288:
                print(f"Error: QBE file '{filepath}' is not 288 bytes long.")
                return None

            # Read data in big-endian format as short integers (2 bytes)
            offset = 0
            for i in range(MAX_TRANSFORMS):
                val = struct.unpack('>H', buf[offset : offset+2])[0]
                info.transform_sequence[i] = TransformType(val % NUM_TRANSFORM_TYPES)
                offset += 2
            
            for i in range(MAX_TRANSFORMS):
                val = struct.unpack('>H', buf[offset : offset+2])[0]
                info.source[i] = val % NUM_REGISTERS
                offset += 2

            for i in range(MAX_TRANSFORMS):
                val = struct.unpack('>H', buf[offset : offset+2])[0]
                info.control[i] = val % NUM_REGISTERS
                offset += 2

            for i in range(MAX_TRANSFORMS):
                val = struct.unpack('>H', buf[offset : offset+2])[0]
                info.dest[i] = val % NUM_REGISTERS
                offset += 2
        return info
    except FileNotFoundError:
        print(f"Error: File not found '{filepath}'")
        return None
    except Exception as e:
        print(f"Error loading QBE file '{filepath}': {e}")
        return None

def save_qbe_data(filepath: str, info: ExpInfo):
    """
    Saves the Qbist pattern data from an ExpInfo object to a .qbe file.
    The data is stored as a raw binary dump.

    Args:
        filepath: The path where the .qbe file will be saved.
        info: The ExpInfo object containing the pattern data.

    Returns:
        True if successful, False otherwise.
    """
    try:
        with open(filepath, "wb") as f:
            buf = bytearray(288)
            offset = 0
            
            for i in range(MAX_TRANSFORMS):
                struct.pack_into('>H', buf, offset, info.transform_sequence[i].value)
                offset += 2
            
            for i in range(MAX_TRANSFORMS):
                struct.pack_into('>H', buf, offset, info.source[i])
                offset += 2

            for i in range(MAX_TRANSFORMS):
                struct.pack_into('>H', buf, offset, info.control[i])
                offset += 2

            for i in range(MAX_TRANSFORMS):
                struct.pack_into('>H', buf, offset, info.dest[i])
                offset += 2
            
            f.write(buf)
        return True
    except Exception as e:
        print(f"Error saving QBE file '{filepath}': {e}")
        return False

def is_image_monochrome(pixel_data, width, height):
    arr = np.frombuffer(pixel_data, dtype=np.uint8).reshape((height, width, 4))
    rgb = arr[..., :3]
    stddev = np.std(rgb, axis=(0, 1))
    return np.all(stddev < 2)  # Schwellenwert ggf. anpassen
