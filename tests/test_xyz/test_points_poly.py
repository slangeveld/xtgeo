# -*- coding: utf-8 -*-
import pytest
import numpy as np
from xtgeo.xyz import XYZ
from xtgeo.xyz import Points
from xtgeo.xyz import Polygons

from xtgeo.common import XTGeoDialog
import test_common.test_xtg as tsetup

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__)

if not xtg.testsetup():
    raise SystemExit

td = xtg.tmpdir
testpath = xtg.testpath

skiplargetest = pytest.mark.skipif(xtg.bigtest is False,
                                   reason='Big tests skip')

# =========================================================================
# Do tests
# =========================================================================

PFILE1A = '../xtgeo-testdata/polygons/reek/1/top_upper_reek_faultpoly.zmap'
PFILE1B = '../xtgeo-testdata/polygons/reek/1/top_upper_reek_faultpoly.xyz'
PFILE1C = '../xtgeo-testdata/polygons/reek/1/top_upper_reek_faultpoly.pol'
PFILE = '../xtgeo-testdata/points/eme/1/emerald_10_random.poi'
POLSET2 = '../xtgeo-testdata/polygons/reek/1/polset2.pol'
POINTSET2 = '../xtgeo-testdata/points/reek/1/pointset2.poi'


def test_xyz():
    """Import XYZ module from file, should not be possible as it is abc."""

    ok = False
    try:
        myxyz = XYZ()
    except TypeError as tt:
        ok = True
        logger.info(tt)
        assert 'abstract' in str(tt)
    else:
        logger.info(myxyz)

    assert ok is True


def test_import():
    """Import XYZ points from file."""

    mypoints = Points(PFILE)  # should guess based on extesion

    logger.debug(mypoints.dataframe)

    x0 = mypoints.dataframe['X_UTME'].values[0]
    logger.debug(x0)
    tsetup.assert_almostequal(x0, 460842.434326, 0.001)


def test_import_zmap_and_xyz():
    """Import XYZ polygons on ZMAP and XYZ format from file"""

    mypol2a = Polygons()
    mypol2b = Polygons()
    mypol2c = Polygons()

    mypol2a.from_file(PFILE1A, fformat='zmap')
    mypol2b.from_file(PFILE1B)
    mypol2c.from_file(PFILE1C)

    assert mypol2a.nrow == mypol2b.nrow
    assert mypol2b.nrow == mypol2c.nrow

    logger.info(mypol2a.nrow, mypol2b.nrow)

    logger.info(mypol2a.dataframe)
    logger.info(mypol2b.dataframe)

    for col in ['X_UTME', 'Y_UTMN', 'Z_TVDSS', 'POLY_ID']:
        status = np.allclose(mypol2a.dataframe[col].values,
                             mypol2b.dataframe[col].values)

        assert status is True


def test_import_export_polygons():
    """Import XYZ polygons from file. Modify, and export."""

    mypoly = Polygons()

    mypoly.from_file(PFILE, fformat='xyz')

    z0 = mypoly.dataframe['Z_TVDSS'].values[0]

    tsetup.assert_almostequal(z0, 2266.996338, 0.001)

    logger.debug(mypoly.dataframe)

    mypoly.dataframe['Z_TVDSS'] += 100

    mypoly.to_file(td + '/polygon_export.xyz', fformat='xyz')

    # reimport and check
    mypoly2 = Polygons(td + '/polygon_export.xyz')

    tsetup.assert_almostequal(z0 + 100,
                              mypoly2.dataframe['Z_TVDSS'].values[0], 0.001)


def test_polygon_boundary():
    """Import XYZ polygons from file and test boundary function."""

    mypoly = Polygons()

    mypoly.from_file(PFILE, fformat='xyz')

    boundary = mypoly.get_boundary()

    tsetup.assert_almostequal(boundary[0], 460595.6036, 0.0001)
    tsetup.assert_almostequal(boundary[4], 2025.952637, 0.0001)
    tsetup.assert_almostequal(boundary[5], 2266.996338, 0.0001)


def test_points_in_polygon():
    """Import XYZ points and do operations if inside or outside"""

    poi = Points(POINTSET2)
    pol = Polygons(POLSET2)
    print(poi.dataframe)

    poi.operation_polygons(pol, 0, opname='eli',
                           where=True)

    print(poi.dataframe)
    poi.to_file('TMP/poi_test.poi')
