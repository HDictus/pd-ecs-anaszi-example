from pathlib import Path
import numpy as np
import anasazi as test_module
import anasazi.components as comps
import pd_ecs


TERRAIN_FILE = Path(__file__).parent / 'data' / 'yields 800-805.npy'


def test_load_terrain():
    
    terrain_data = test_module.load_terrain(
        TERRAIN_FILE, 800, 
        soil_quality_variance=0.0, 
        coeff_var=0.2)
    
    rawdata = np.load(TERRAIN_FILE)
    
    assert all(terrain_data['var'] == 0.2 * terrain_data['mean'])
    for (t, x, y), v in np.ndenumerate(rawdata):
        assert terrain_data.loc[(t+800, x, y), 'mean'] == v


TERRAIN_DATA = test_module.load_terrain(
    TERRAIN_FILE, 800, soil_quality_variance=0.1, coeff_var=2)

def test_initialize_terrain():
    world = pd_ecs.World()
    test_module.initialize_terrain(
        world,
        TERRAIN_DATA,
        year=800
    )
    assert np.allclose(
        world[comps.POSITION].values,
        TERRAIN_DATA.loc[800].reset_index()[['x', 'y']].values)
    assert np.allclose(
        world[comps.YIELD].values,
        TERRAIN_DATA.loc[800, ['mean', 'var']].values
    )
    assert all(world[comps.OCCUPYING_HOMES] == 0)

def test_update_terrain():
    # hurr durr not sure how to test
    assert False