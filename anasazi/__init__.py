import numpy as np
from pathlib import Path
import pandas as pd
import anasazi.components as comp

# I think the choices of components here illustrate just how not-immune an ECS is to adding logic assumptions into the data
# ....
# what if a thingy has multiple stockpiles (storage locations) e.g. for different goods?
# TODO: we really need a naming convention for components.
# or a namespace...


def harvest(world, max_grain_stock=1600):
    households = world[(comp.stockpile, comp.farmland)]
    land = world[comp.grain_yield]
    harvest_statistics = land.loc[households[comp.farmland]['id']]
    harvest = np.random.normal(
        harvest_statistics['mean'].values, harvest_statistics['var'].values)
    grain_stockpile = households[comp.stockpile]
    grain_stockpile['grain'] += harvest
    world.update({comp.stockpile: grain_stockpile})
