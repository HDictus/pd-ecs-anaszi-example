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

    def mock_norm(mean, var):
        return mean + var

    oldnorm = np.random.normal
    np.random.normal = mock_norm
    harvest_grain(world, max_grain_stock=250)
    np.random.normal = oldnorm
    assert np.allclose(world[comps.STOCKPILE]['grain'].values, [125, 250, 60])


def test_terrain_updates():
    # hurr durr not sure how to test
    terrain_file = Path(__file__).parent / 'data' / 'yields 800-805.npy'
    terrain_data = load_terrain(terrain_file, 800,
                                soil_quality_variance=0.1, coeff_var=0.2)
