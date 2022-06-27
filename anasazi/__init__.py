import numpy as np
from pathlib import Path
import pandas as pd
from pd_ecs import Component, System

position = Component("x", "y")
grain_yield = Component('mean', 'var')
stockpile = Component("grain")
farmland = Component('id')


class HarvestSystem(System):

    filters = dict(households=[position, stockpile, farmland],
                   land=[position, grain_yield])

    max_grain_stock = 1600

    def __init__(self, world,
                 yield_data=None,
                 soil_quality_variance=0.4, harvest_variance=2,
                 rng=None):
        super().__init__(world)

        self.rng = rng or np.random.default_rng()
        if yield_data is None:
            yield_data = np.load(Path(__file__).parent.parent / "yields 800-1349.npy")

        soil_qualtity = 1 + (self.rng.normal(
            0, soil_quality_variance, size=yield_data.shape[1:]))

        self.yield_mean_by_year = yield_data * soil_qualtity
        self.harvest_variance = harvest_variance
        self.world.mapsize = yield_data[0].shape
        self._yield_index = None
        self.initialize()

    @property
    def mean_this_year(self):
        if self._yield_index is None:
            self._yield_index = 0
        return self.yield_mean_by_year[self._yield_index]

    def initialize(self):
        mean_this_year = self.mean_this_year
        x = []
        y = []
        mean = []
        var = []
        for (i, j), mn in np.ndenumerate(mean_this_year):
            x.append(i)
            y.append(j)
            mean.append(mn)
            var.append(mn * self.harvest_variance)
        self.world.add_entities(
            {grain_yield: dict(mean=mean,
                               var=var),
             position: dict(x=x, y=y)})

    def calculate_yield(self, farm_ids):
        grainyields = self.world[grain_yield].loc[farm_ids]
        return np.random.normal(grainyields['mean'], grainyields['std'])

    def year_passes(self):
        self._yield_index += 1
        mean = self.mean_this_year.flatten()
        var = self.harvest_variance * mean
        self.world[grain_yield].loc[self.land.index, 'mean'] = mean
        self.world[grain_yield].loc[self.land.index, 'var'] = var
        farm_ids = self.world[farmland].loc[self.households.index, 'id'].values

        yields = self.world[grain_yield].loc[farm_ids]
        harvest = self.rng.normal(yields['mean'], yields['var'])
        self.world.events.harvest(self.households.index, harvest)

    def harvest(self, households, harvests):
        self.world[stockpile].loc[households, 'grain'] = np.clip(
            self.world[stockpile].loc[households, 'grain'] + harvests,
            0, self.max_grain_stock)
        print(self.world[stockpile])
        return
