import numpy as np
import pandas as pd
import pkg_resources
from pathlib import Path
from pd_ecs import World
from anasazi import harvest_grain, initialize_terrain, update_terrain, load_terrain
from anasazi.components import position, grain_yield, stockpile, farmland, time
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


def test_terrain_updates():
    # this tests fuck all.
    terrain_file = Path(__file__).parent / 'data' / 'yields 800-805.npy'
    terrain_data = load_terrain(terrain_file, 800,
                                soil_quality_variance=0.1, coeff_var=0.2)
    world = World()
    world.add_entities({time: {'year': [800]}})
    initialize_terrain(world, terrain_data)
    yield_and_posn = pd.concat([world[grain_yield], world[position]], axis=1)
    year800 = terrain_data[terrain_data.year == 800]
    assert yield_and_posn.set_index(['x', 'y']) == year800.set_index(['x, y'])

    assert all(world[grain_yield]['mean'].values == terrain_data.set_index(['year').loc[800]['mean'])
    print(world[grain_yield]['mean'])
    print(terrain_data.set_index('year').loc[800, 'mean'])
    assert all(world[grain_yield]['var'].values == terrain_data.set_index('year').loc[800]['mean'] * 0.2)
    world[time]['year'] = 805
    update_terrain(world, terrain_data)
    assert all(world[grain_yield]['mean'].values == terrain_data.set_index('year').loc[805]['mean'])
    assert all(world[grain_yield]['var'].values == terrain_data.set_index('year').loc[805]['mean'] * 0.2)
