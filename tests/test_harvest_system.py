import numpy as np
import pandas as pd
from pathlib import Path
from pd_ecs import World
from anasazi import harvest_grain
from anasazi.components import position, grain_yield, stockpile, farmland
from mock import MagicMock


def test_harvest():
    world = World()
    land = world.add_entities({grain_yield: {'mean': [100, 200, 0], 'var': [25, 50, 0]}})
    homes = world.add_entities({stockpile: {'grain': [0, 25, 60]},
                                farmland: {'id': land}})

    def mock_norm(mean, var):
        return mean + var

    oldnorm = np.random.normal
    np.random.normal = mock_norm
    harvest_grain(world, max_grain_stock=250)
    np.random.normal = oldnorm
    assert np.allclose(world[stockpile]['grain'].values, [125, 250, 60])
