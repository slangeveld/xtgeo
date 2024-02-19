import pathlib

import numpy as np
import pytest
import xtgeo
from xtgeo.common import XTGeoDialog

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__)

RPATH1 = pathlib.Path("surfaces/reek")
RPATH2 = pathlib.Path("3dgrids/reek")

RTOP1 = RPATH1 / "1/topreek_rota.gri"
RGRD1 = RPATH2 / "REEK.EGRID"
RPROP1 = RPATH2 / "REEK.INIT"
RGRD2 = RPATH2 / "reek_sim_grid.roff"
RPROP2 = RPATH2 / "reek_sim_zone.roff"


def test_get_surface_from_grd3d_porosity(tmp_path, generate_plot, testdata_path):
    """Sample a surface from a 3D grid"""

    surf = xtgeo.surface_from_file(testdata_path / RTOP1)
    print(surf.values.min(), surf.values.max())
    grd = xtgeo.grid_from_file(testdata_path / RGRD1, fformat="egrid")
    surf.values = 1700
    zsurf = surf.copy()
    surfr = surf.copy()
    surf2 = surf.copy()
    phi = xtgeo.gridproperty_from_file(
        testdata_path / RPROP1, fformat="init", name="PORO", grid=grd
    )

    # slice grd3d
    surf.slice_grid3d(grd, phi)

    surf.to_file(tmp_path / "surf_slice_grd3d_reek.gri")
    if generate_plot:
        surf.quickplot(filename=tmp_path / "surf_slice_grd3d_reek.png")

    # refined version:
    surfr.refine(2)
    surfr.slice_grid3d(grd, phi)

    surfr.to_file(tmp_path / "surf_slice_grd3d_reek_refined.gri")
    if generate_plot:
        surfr.quickplot(filename=tmp_path / "surf_slice_grd3d_reek_refined.png")

    # use zsurf:
    surf2.slice_grid3d(grd, phi, zsurf=zsurf)

    surf2.to_file(tmp_path / "surf_slice_grd3d_reek_zslice.gri")
    if generate_plot:
        surf2.quickplot(filename=tmp_path / "surf_slice_grd3d_reek_zslice.png")

    assert np.allclose(surf.values, surf2.values)

    assert surf.values.mean() == pytest.approx(0.1667, abs=0.01)
    assert surfr.values.mean() == pytest.approx(0.1667, abs=0.01)


def test_get_surface_from_grd3d_zones(tmp_path, generate_plot, testdata_path):
    """Sample a surface from a 3D grid, using zones"""

    surf = xtgeo.surface_from_file(testdata_path / RTOP1)
    grd = xtgeo.grid_from_file(testdata_path / RGRD2, fformat="roff")
    surf.values = 1700
    zone = xtgeo.gridproperty_from_file(
        testdata_path / RPROP2, fformat="roff", name="Zone", grid=grd
    )

    # slice grd3d
    surf.slice_grid3d(grd, zone, sbuffer=1)

    surf.to_file(tmp_path / "surf_slice_grd3d_reek_zone.gri")
    if generate_plot:
        surf.quickplot(filename=tmp_path / "surf_slice_grd3d_reek_zone.png")


@pytest.mark.filterwarnings("ignore:Default values*")
def test_surface_from_grd3d_layer(
    tmp_path, generate_plot, default_surface, testdata_path
):
    """Create a surface from a 3D grid layer"""

    surf = xtgeo.RegularSurface(**default_surface)
    grd = xtgeo.grid_from_file(testdata_path / RGRD2, fformat="roff")
    surf = xtgeo.surface_from_grid3d(grd)

    surf.fill()
    surf.to_file(tmp_path / "surf_from_grid3d_top.gri")
    tmp = surf.copy()
    if generate_plot:
        surf.quickplot(filename=tmp_path / "surf_from_grid3d_top.png")

    surf = xtgeo.surface_from_grid3d(grd, template=tmp, mode="i")

    surf.to_file(tmp_path / "surf_from_grid3d_top_icell.gri")
    if generate_plot:
        surf.quickplot(filename=tmp_path / "surf_from_grid3d_top_icell.png")

    surf = xtgeo.surface_from_grid3d(grd, template=tmp, mode="j")
    surf.fill()
    surf.to_file(tmp_path / "surf_from_grid3d_top_jcell.gri")
    if generate_plot:
        surf.quickplot(filename=tmp_path / "surf_from_grid3d_top_jcell.png")

    surf = xtgeo.surface_from_grid3d(grd, template=tmp, mode="depth", where="3_base")
    surf.to_file(tmp_path / "surf_from_grid3d_3base.gri")
    if generate_plot:
        surf.quickplot(filename=tmp_path / "surf_from_grid3d_3base.png")
