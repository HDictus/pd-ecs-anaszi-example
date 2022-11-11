import numpy as np
from pathlib import Path
import pandas as pd
from pd_ecs import Component, System

position = Component("x", "y", name='position')
grain_yield = Component('mean', 'var', name='yield')
food_needs = Component('grain', name='yearly food needed (Kg corn)')
stockpile = Component("grain", name='stockpile')
farmland = Component('id', name='farmland')
occupying_farms = Component('num occupants')
occupying_houses = Component('num occupants')


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
        land = self.land[grain_yield]
        land['mean'] = mean
        land['var'] = var
        farm_ids = self.households[farmland]['id']
        yields = land.loc[farm_ids]
        harvest = self.rng.normal(yields['mean'], yields['var'])
        self.world.events.harvest(self.households.ids, harvest)
        self.world.update({grain_yield: land})

    def harvest(self, households, harvests):
        self.world[stockpile].loc[households, 'grain'] = np.clip(
            self.world[stockpile].loc[households, 'grain'] + harvests,
            0, self.max_grain_stock)
        return


KG_GRAIN_PER_YEAR = 160 * 5  # 160kg grain per year, household avg of 5 people


class EatingSystem(System):

    filters = dict(households=[stockpile])

    def __init__(self, world, yearly_grain=KG_GRAIN_PER_YEAR):
        super().__init__(world)
        self.yearly_grain = yearly_grain

    def year_passes(self):
        stockpiles = self.households[stockpile]
        stockpiles['grain'] -= self.yearly_grain
        self.world.update({stockpile: stockpiles})


class MovingSystem(System):

    # TODO: maybe it would be cleaner to have only occupied land have the
    # occupying farms and occupying houses components, and so we can
    # just ~ them in the filter.
    # would need a new component: is_land
    filters = dict(arable_land=[position, grain_yield, occupying_farms,
                                occupying_houses],
                   potential_housing=[position, occupying_houses,
                                      occupying_farms])

    def harvest(self, ids, amount):
        ids = np.array(ids)
        expected_next_year = amount + self.world[stockpile].loc[ids, 'grain']
        expects_to_starve = ids[
            self.world[food_needs].loc[ids, 'grain'] > expected_next_year]

        self.world.events.find_home(expects_to_starve)

    def find_home(self, ids):
        positions, yields, occupation, houses = self.arable_land.data()
        mover_positions = self.world[position].loc[ids]
        mover_needs = self.world[food_needs].loc[ids]
        unoccupied = np.logical_and(
            occupation['num occupants'] == 0,
            houses['num occupants'] == 0)
        positions = positions[unoccupied]
        yields = yields[unoccupied]
        displacements = (
            positions.values[np.newaxis, ...]
            - mover_positions.values[..., np.newaxis, :]
        )
        distances = np.linalg.norm(displacements, axis=-1)
        enough_to_survive = (
            yields['mean'].values[np.newaxis, ...]
            >= mover_needs['grain'].values[..., np.newaxis]
        )
        distances[~enough_to_survive] = np.inf
        nearest_farms = []
        for dist in distances:
            if not np.isfinite(dist).any():
                assert False, "lol, TODO"
            nearest = np.argmin(dist)
            distances[:, nearest] = np.inf
            nearest_farms.append(positions.index[nearest])

        self.world.give(ids, {farmland: {'id': nearest_farms}})

        self.world[occupying_farms].loc[nearest_farms] += 1
        # TODO: there is a repeated operation here I should abstract away
        # TODO: should there maybe be a filter???

        house_posns, occupants, farmed = self.potential_housing.data()
        potential_house_positions = house_posns[farmed['num occupants'] == 0]

        house_to_farm_distance = np.linalg.norm(
            potential_house_positions.values[np.newaxis, ...]
            - positions.loc[nearest_farms].values[..., np.newaxis, :],
            axis=-1
        )
        houses = potential_house_positions.iloc[
            np.argmin(house_to_farm_distance, axis=1)]
        self.world[position].loc[ids] = houses.values
        house_ids, nhouses = np.unique(houses.index, return_counts=True)

        self.world[occupying_houses].loc[house_ids] += nhouses
