import numpy as np
import pandas as pd
from pathlib import Path
from pd_ecs import World
from anasazi import position, grain_yield, stockpile, farmland, HarvestSystem
from mock import MagicMock


def test_system_updates_yield_yearly():
    world = World(grain_yield, position, stockpile, farmland)
    data = np.load(Path(__file__).parent.parent / "yields 800-1349.npy")
    # TODO: maybe csv would be better?
    # how should it interact with yearsystem?
    rng = np.random.default_rng(0)
    soil_quality_variance = 0.4
    harvest_variance = 0.5
    expected_mean = data[0].flatten()
    soil_quality = 1 + rng.normal(0, soil_quality_variance,
                                  size=expected_mean.shape)
    expected_mean *= soil_quality

    sys = HarvestSystem(world, yield_data=data, rng=np.random.default_rng(0),
                        soil_quality_variance=soil_quality_variance,
                        harvest_variance=harvest_variance)
    pd.testing.assert_frame_equal(
        world[grain_yield],
        pd.DataFrame({'mean': expected_mean,
                      'var': harvest_variance * expected_mean}))
    sys.year_passes()
    oldmean = expected_mean
    expected_mean = data[1].flatten() * soil_quality

    pd.testing.assert_frame_equal(
        world[grain_yield],
        pd.DataFrame({'mean': expected_mean,
                      'var': harvest_variance * expected_mean}))
    return


def test_system_calls_harvest_event():
    world = World(grain_yield, position, stockpile, farmland)
    print(world[farmland])
    world.events.harvest = MagicMock()
    data = np.load(Path(__file__).parent.parent / "yields 800-1349.npy")
    sys = HarvestSystem(world, yield_data=data,
                        harvest_variance=0)
    hhlds = world.add_entities({
        position: dict(x=np.random.randint(0, 100, size=5), y=np.random.randint(0, 100, size=5)),
        stockpile: dict(grain=0),
        farmland: dict(id=[0, 1, 2, 3, 4])})
    sys.year_passes()
    yields = world[grain_yield].loc[[0, 1, 2, 3, 4]]

    arg1, arg2 = world.events.harvest.mock_calls[0].args
    assert np.allclose(arg1, hhlds)
    assert np.allclose(arg2, yields['mean'])
