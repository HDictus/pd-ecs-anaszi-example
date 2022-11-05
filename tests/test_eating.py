import numpy as np
import pandas as pd
from pd_ecs import World
from anasazi import EatingSystem, stockpile, food_needs


def test_eat_each_year():
    world = World(stockpile, food_needs)
    world.set_state({
        stockpile: pd.DataFrame({'grain': [22, 22, 30, 35]}),
        food_needs: pd.DataFrame({'grain': [10, 10, 10, 10]})})

    es = EatingSystem(world, yearly_grain=10)
    world.events.year_passes()
    assert np.allclose(world[stockpile]['grain'], [12, 12, 20, 25])
