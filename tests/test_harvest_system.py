import numpy as np
import pandas as pd
import pkg_resources
from pathlib import Path
from pd_ecs import World
from anasazi import harvest_grain, initialize_terrain, update_terrain, load_terrain
from anasazi import components as comps
from mock import MagicMock


def test_harvest():
    world = World()
    land = world.add_entities({comps.YIELD: {'mean': [100, 200, 0], 'var': [25, 50, 0]}})
    homes = world.add_entities({comps.STOCKPILE: {'grain': [0, 25, 60]},
                                comps.FARMLAND: {'id': land}})

    def mock_norm(loc, scale):
        return loc + scale

    oldnorm = np.random.normal
    np.random.normal = mock_norm
    harvest_grain(world, max_grain_stock=250)
    np.random.normal = oldnorm
    assert np.allclose(world[comps.STOCKPILE]['grain'].values, [125, 250, 60])

