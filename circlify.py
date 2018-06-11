#!/usr/bin/env python
# encoding: utf-8

"""Basic circle packing algorithm based on 2 algorithms.

Circles are first arranged via a version of A1.0 by Huang et al (see
https://home.mis.u-picardie.fr/~cli/Publis/circle.pdf for details) and then a
an enclosure circle is created around them using the same algorithm used in 
d3js (see ?)

"""

import sys
import math
from math import sqrt, pi
import collections
import itertools
import logging
import random


__version__ = '0.1'

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as pltp

    def bubbles(circles, e=None, lim=None):
        """Debugging function displays circles."""
        x, y, s, labels = [], [], [], []
        fig, ax = plt.subplots(figsize=(8.0, 8.0))
        for label in circles:
            x, y, r = circles[label]
            ax.add_patch(pltp.Circle((x, y), r, alpha=0.2,
                                     linewidth=2, fill=False))
            ax.text(x, y, label)
            labels.append(label)
        if e:
            ax.add_patch(pltp.Circle((e.x, e.y), e.r, alpha=0.2,
                                     linewidth=2, color='red'))
        if lim is None:
            lim = max([max(abs(c.x) + c.r, abs(c.y) + c.r)
                       for c in circles.values()])
        plt.xlim(-lim, lim)
        plt.ylim(-lim, lim)
        plt.show()
except ImportError:
    pass


Circle = collections.namedtuple('Circle', ['x', 'y', 'r'])

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def distance(circle1, circle2):
    """Compute distance between 2 cirlces."""
    x1, y1, r1 = circle1
    x2, y2, r2 = circle2
    x = x2 - x1
    y = y2 - y1
    return sqrt(x * x + y * y) - r1 - r2


def get_intersection(circle1, circle2):
    """Calculate intersections of 2 circles

    Based on https://gist.github.com/xaedes/974535e71009fa8f090e
    Credit to http://stackoverflow.com/a/3349134/798588

    Returns:
        2 pairs of coordinates. Each pair can be None if there are no or just
        one intersection.

    """
    x1, y1, r1 = circle1
    x2, y2, r2 = circle2
    dx, dy = x2 - x1, y2 - y1
    d = sqrt(dx * dx + dy * dy)
    if d > r1 + r2:
        log.debug('no solution, the circles are separate: %s, %s',
                  circle1, circle2)
        return None, None
    if d < abs(r1 - r2):
        log.debug('no solution, circles contained within each other: %s, %s',
                  circle1, circle2)
        return None, None
    if d == 0 and r1 == r2:
        log.debug('no solution, circles are coincident: %s, %s',
                  circle1, circle2)
        return None, None
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = sqrt(r1 * r1 - a * a)
    xm = x1 + a * dx / d
    ym = y1 + a* dy / d
    xs1 = xm + h * dy / d
    xs2 = xm - h * dy / d
    ys1 = ym - h * dx / d
    ys2 = ym + h * dx / d
    if xs1 == xs2 and ys1 == ys2:
        return (xs1, ys1), None
    return (xs1, ys1), (xs2, ys2)


def get_placement_candidates(radius, c1, c2):
    """Generate placement candidates for 2 existing placed circles.

    Args:
        radius: radius of the new circle to place.
        c1: first existing placed circle.
        c2: second existing placed circle.

    Returns:
        A pair of candidate cirlces where one or both value can be None.

    """
    margin = 10.0 * sys.float_info.epsilon
    ic1 = Circle(c1.x, c1.y, c1.r + (radius + margin))
    ic2 = Circle(c2.x, c2.y, c2.r + (radius + margin))
    i1, i2 = get_intersection(ic1, ic2)
    if i1 is None:
        return None, None
    candidate1 = Circle(*i1, radius)
    if i2 is None:
        return candidate1, None
    candidate2 = Circle(*i2, radius)
    return candidate1, candidate2


def get_hole_degree(candidate, placed_circles, pc1, pc2):
    """Calculate the hole degree of a candidate circle.

    Note pc1 and pc2 must not be used in the evaluation of the minimum
    distance.

    Args:
        candidate: candidate circle.
        placed_circles: sequence of circles already placed.
        pc1: first placed circle used to place the candidate.
        pc2: second placed circle used to place the candidate.

    Returns:
        hole degree defined as (1 - d_min / r_i) where d_min is a minimum
        disance between the candidate and the circles other than the one
        used to place the candidate and r_i the radius of the candidate.

    """
    #min_dist = None
    lsq = 0.
    for pc in placed_circles:
        if pc1 is not None and pc1 == pc:
            continue
        if pc2 is not None and pc2 == pc:
            continue
        lsq += sqrt((candidate.y - pc.y) ** 2.0 + (candidate.x - pc.x) ** 2.0)
        #if min_dist is None or min_dist > dist:
            #min_dist = dist
    #if min_dist is None:
        #return 0.0
    return -sqrt(lsq)


def pack_A1_0(data):
    """Pack circles whose radius is linked to the input data.

    This algorithm is loosely based on the Huang et al. heuristic. See
    https://home.mis.u-picardie.fr/~cli/Publis/circle.pdf.

    Args:
        data: dict-like variable with label, value to circlify.

    Returns:
        dict with a circ.Circle as value for each label.

    """
    placed_circles = {}
    for label in sorted(data, key=data.get, reverse=True):
        radius = sqrt(data[label])
        n_circles = len(placed_circles)
        # Place first 2 circles on each side of (0, 0)
        if n_circles <= 1:
            x = radius if n_circles == 0 else -radius
            circle = Circle(x, 0.0, radius)
            placed_circles[label] = circle
            continue
        mhd = None
        lead_candidate = None
        for (c1, c2) in itertools.combinations(placed_circles.values(), 2):
            for cand in get_placement_candidates(radius, c1, c2):
                if cand is not None:
                    # Ignore candidates that overlap with any placed circle.
                    overlap = False
                    for pc in placed_circles.values():
                        if distance(pc, cand) < 0.0:
                            overlap = True
                            break
                    if overlap:
                        continue
                    hd = get_hole_degree(cand, placed_circles.values(), c1, c2)
                    if mhd is None or hd > mhd:
                        mhd = hd
                        lead_candidate = cand
        if lead_candidate is None:
            log.info('cannot place circle for data %s', label)
            break
        placed_circles[label] = lead_candidate
    return placed_circles


def extendBasis(B, p):
    """Extend basis to ...  """
    if enclosesWeakAll(p, B):
        return [p];

    # If we get here then B must have at least one element.
    for i in range(len(B)):
        if enclosesNot(p, B[i]) and enclosesWeakAll(encloseBasis2(B[i], p), B):
            return [B[i], p];

    # If we get here then B must have at least two elements.
    for i in range(len(B) - 1):
        for j in range(i + 1, len(B)):
            if enclosesNot(encloseBasis2(B[i], B[j]), p) and \
                    enclosesNot(encloseBasis2(B[i], p), B[j]) and \
                    enclosesNot(encloseBasis2(B[j], p), B[i]) and \
                    enclosesWeakAll(encloseBasis3(B[i], B[j], p), B):
                return [B[i], B[j], p];
    raise RuntimeError('If we get here then something is very wrong')


def enclosesNot(a, b):
    dr = a.r - b.r
    dx = b.x - a.x
    dy = b.y - a.y
    return dr < 0 or dr * dr < dx * dx + dy * dy


def enclosesWeak(a, b):
    dr = a.r - b.r + 1e-6
    dx = b.x - a.x
    dy = b.y - a.y
    return dr > 0 and dr * dr > dx * dx + dy * dy


def enclosesWeakAll(a, B):
    for i in range(len(B)):
        if not enclosesWeak(a, B[i]):
            return False
    return True


def encloseBasis(B):
    if len(B) == 1:
        return B[0]
    elif len(B) == 2:
        return encloseBasis2(B[0], B[1])
    else:
        return encloseBasis3(B[0], B[1], B[2])


def encloseBasis2(a, b):
    x1, y1, r1 = a.x, a.y, a.r
    x2, y2, r2 = b.x, b.y, b.r
    x21 = x2 - x1
    y21 = y2 - y1
    r21 = r2 - r1
    l = sqrt(x21 * x21 + y21 * y21);
    return Circle((x1 + x2 + x21 / l * r21) / 2,
                  (y1 + y2 + y21 / l * r21) / 2,
                  (l + r1 + r2) / 2)


def encloseBasis3(a, b, c):
    x1, y1, r1 = a.x, a.y, a.r
    x2, y2, r2 = b.x, b.y, b.r
    x3, y3, r3 = c.x, c.y, c.r
    a2 = x1 - x2
    a3 = x1 - x3
    b2 = y1 - y2
    b3 = y1 - y3
    c2 = r2 - r1
    c3 = r3 - r1
    d1 = x1 * x1 + y1 * y1 - r1 * r1
    d2 = d1 - x2 * x2 - y2 * y2 + r2 * r2
    d3 = d1 - x3 * x3 - y3 * y3 + r3 * r3
    ab = a3 * b2 - a2 * b3
    xa = (b2 * d3 - b3 * d2) / (ab * 2) - x1
    xb = (b3 * c2 - b2 * c3) / ab
    ya = (a3 * d2 - a2 * d3) / (ab * 2) - y1
    yb = (a2 * c3 - a3 * c2) / ab
    A = xb * xb + yb * yb - 1
    B = 2 * (r1 + xa * xb + ya * yb)
    C = xa * xa + ya * ya - r1 * r1
    if A != 0.0:
        r = -(B + sqrt(B * B - 4 * A * C)) / (2 * A)
    else:
        r = -C / B
    return Circle(x1 + xa + xb * r, y1 + ya + yb * r, r)


def scale(circles, x, y, r):
    """Scale cirlces in enclosure to fit in the unit circle.

    Args:
        circles: dict of label and Circle objects to scale.
        x, y, r: coordinates and radius to scale to.

    Returns:
        scaled circles as dict of label and Circles.

    """
    scaled = {}
    for label in circles:
        x_c, y_c, r_c = circles[label]
        scaled[label] = Circle((x_c - x) / r, (y_c - y) / r, r_c / r)
    return scaled


def enclose(packed_circles):
    B = []
    p, e = None, None
    circles = [c for c in packed_circles.values()]
    random.shuffle(circles)

    n = len(circles)
    i = 0
    while i < n:
        p = circles[i];
        if e is not None and enclosesWeak(e, p):
            i = i + 1
        else:
            B = extendBasis(B, p)
            e = encloseBasis(B)
            i = 0
        #import pdb; pdb.set_trace()
        #bubbles(packed_circles, e)
    return e


def circlify(data, with_unit=False):
    """Pack and enclose circles whose radius is linked to the input data.

    Args:
        data: dict-like variable with label, value to circlify.
        with_unit: adds the unit circle to the output if True.

    Returns:
        dict with a circ.Circle as value for each label.

    """
    packed_circles = pack_A1_0(data)
    enclosure = enclose(packed_circles)
    packed_and_scaled_circles = scale(packed_circles, *enclosure)
    if with_unit:
        packed_and_scaled_circles[''] = Circle(0, 0, 1)
    return packed_and_scaled_circles

