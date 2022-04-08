from pd_ecs import World, System, Component
import numpy as np
from scipy.ndimage import gaussian_filter

# for now we just do farming on a random map with random changes

YEARS_PER_SECOND = 5


# TODO: technically the map data should not be attached to a system, but
#    should be an entity somehow
# TODO: better as kwargs name: type?
# TODO: are we sure farmland should be its own entity?
#   it is removed when a household is removed
# TODO: test-driven refactoring is very important

position = Component("x", "y")
stockpile = Component("grain")
farmland = Component('id')
grain_yield = Component('mean', 'std')


def initialize_households(world, n_households, initial_grain=1600):
    positions = np.array(
        [[x, y]
         for x in range(world.mapsize[0])
         for y in range(world.mapsize[1])])
    xy = positions[np.random.choice(range(len(positions)), n_households, replace=False)]
    grain = np.ones((n_households, )) * initial_grain

    farmlands = world.add_entities(
        {position: dict(x=np.zeros(xy[:, 0].shape) + np.nan,
                        y=np.nan),
         grain_yield: dict(mean=np.zeros(xy[:, 0].shape), std=0)})
    # TODO: this is silly
    households_data = {position: dict(x=xy[:, 0], y=xy[:, 1]),
                       stockpile: dict(grain=grain),
                       age: dict(age=np.zeros(grain.shape)),
                       farmland: dict(id=farmlands)}
    households = world.add_entities(
        households_data)
    world.events.seek_new_farmland(households)
    return


class YearSystem(System):
    time = 0

    def __init__(self, world, start_year=800):
        self.time = start_year / YEARS_PER_SECOND
        super().__init__(world)

    @property
    def year(self):
        return self.time * YEARS_PER_SECOND

    def update(self, dt):
        yearbefore = int(np.floor(self.year))
        self.time += dt
        yearafter = int(np.floor(self.year))
        for i in range(yearafter - yearbefore):
            self.world.events.year_passes()


# TODO: consider systems in isolation, for the needed parameters, what are they to that system?
#    where should they come from?
#    e.g. globals provided at init...
#    or provided to world?


class HarvestSystem(System):

    filters = dict(households = [position, stockpile, farmland],
                   farms= [position, grain_yield])

    max_grain_stock = 1600
    soil_quality_variance = 0.4  # as proportion of yield
    harvest_variance = 2  # as proportion of yield
    # min_yield = 0
    # max_yield = 1650

    def __init__(self, world):
        super().__init__(world)
        # self.yield_mean = np.random.uniform(self.min_yield, self.max_yield, size=world.mapsize)
        # self.yield_mean = gaussian_filter(self.yield_mean, sigma=2)
        # self.yield_std = np.random.uniform(0, 100, size=world.mapsize)
        self.yield_by_year = np.load("yields 800-1349.npy")
        self.yield_by_year *= 1 + (np.random.normal(
            0, self.soil_quality_variance, size=self.yield_by_year.shape[1:]))  # TODO: parameterize
        # self.yield_by_year = gaussian_filter(self.yield_by_year, sigma=0.8)

    @property
    def yield_mean(self):
        year = int(np.floor(self.world.systems[YearSystem].year))
        start_year = 800  # TODO: more example of mixing responsibilities
        yld = self.yield_by_year[year - 800]
        return yld

    def calculate_yield(self, farm_ids):
        grainyields = self.world[grain_yield].loc[farm_ids]
        # stds = self.yield_std
        # actual = np.random.normal(means, stds)
        # actual[actual < 0] = 0
        return np.random.normal(grainyields['mean'], grainyields['std'])

    def mutate_yield(self):
        self.yield_mean += np.random.normal(size=self.yield_mean.shape, scale=0.1)
        # normalized_yield = self.yield_mean - self.yield_mean.mean()
        # self.yield_mean = gaussian_filter(self.yield_mean, sigma=0.01)
        # self.yield_mean += (
        #     0.05 * gaussian_filter(normalized_yield, sigma=0.75)
        #     - 0.01 * normalized_yield**2)
        self.yield_mean[self.yield_mean < 0] = 0

    def year_passes(self):
        # TODO: this could be made better. Ideally we want to only access declared groups.
        # TODO: this is definitely an awkward way to do this. maybe system will automatically refresh after each function call?
        households = self.households.ids
        farm_ids = self.world[farmland].loc[households, 'id']
        harvests = self.calculate_yield(farm_ids)
        self.world.events.harvest(households, harvests)
        # self.mutate_yield()

    def harvest(self, households, harvests):
        # TODO: seems that stockpile requires a system just to manage its mutations
        #   can I make that simpler?
        self.world[stockpile].loc[households, 'grain'] = np.clip(
            self.world[stockpile].loc[households, 'grain'] + harvests,
            0, self.max_grain_stock)
        return


class MovingSystem(System):

    # TODO: can have a maximum distance traveled to keep efficient
    filters=dict(households = [position, stockpile, farmland],
                 farms=[position, grain_yield])

    @property
    def occupied(self):
        occ = np.zeros(self.world.mapsize, dtype=bool)
        posns = np.int32(self.world[position].loc[self.households.ids].values)
        occ[posns[:, 0], posns[:, 1]] = True
        return occ

    @property
    def habitable(self):
        habitable = self.world.systems[HarvestSystem].yield_mean\
            >= self.world.systems[EatingSystem].yearly_consumption
        return habitable

    def harvest(self, households, harvest):
        need = self.world.systems[EatingSystem].yearly_consumption

        expectation = harvest
        grain = self.world[stockpile].loc[households, 'grain']
        harvest_needed = need - grain
        moving = expectation < harvest_needed
        moving_households = households[moving]
        if len(moving_households) > 0:
            self.world.events.seek_new_farmland(moving_households)

    def seek_new_farmland(self, moving_households):
        new_positions, success, homeless = self.new_farmlands(
            moving_households)
        self.world.remove_entities(homeless)

        self.world.events.farms_move(success, new_positions)

    def new_farmlands(self, moving_households):
        available_farmland = list(np.transpose(np.nonzero(
            np.logical_and(~self.occupied, self.habitable))))
        positions = self.world[position].loc[moving_households].values
        moving = []
        homeless = []
        newplaces = []
        for household, posn in zip(moving_households, positions):
            if len(available_farmland) == 0:
                homeless.append(household)
                continue
            index = nearest(posn, np.array(available_farmland))
            moving.append(household)
            newplaces.append(available_farmland.pop(index))
        return newplaces, moving, homeless

    def farms_move(self, movers, new_positions):
        if movers:
            self.world[position].loc[movers] = np.array(new_positions)
        return


def nearest(position, farmland):
    # print(position, farmland, '?????????????')
    dists = np.linalg.norm(position - farmland, axis=1)
    return np.argmin(dists)



class EatingSystem(System):

    filters = dict(households = [position, stockpile])

    yearly_consumption = 160 * 5  # 160 kg of grain p.p., avg 5 per household

    def year_passes(self):
        current_stockpile = self.world[stockpile].loc[self.households.ids, 'grain']
        new_stockpile = current_stockpile - self.yearly_consumption
        starving = current_stockpile.index[new_stockpile < 0]
        self.world[stockpile].loc[self.households.ids, 'grain'] = new_stockpile
        self.world.remove_entities(starving)


import time
import matplotlib.pyplot as plt


# class DeathSystem(System):

#     return


age = Component("age")


class AgeSystem(System):

    filters = dict(ages=[age],
                   households=[age, stockpile])

    move_out_age = 16

    # TODO: fertility, fertility ends age
    death_age = 40
    fertility = 0.155  # chance of having a baby each year

    def year_passes(self):
        """
        Assumptions:
           each household has one child each year after it is established
           every child moves out at 16 years of age
           the child establishes their own household (asexual reproduction)
           every household provides one third of its corn stockpile to the child
           every household dies after exactly 40 years of existing
        # TODO: these various things do not belong in the same system
        #  I would say: fertility age, death age are managed here
        """

        aging_entities = self.ages.ids
        self.world[age].loc[aging_entities, 'age'] += 1
        # TODO: there has to be a way to make the below smoother
        # it shouldn't belong to agesystem
        households = self.households.ids
        moving_out = np.logical_and(
            np.random.uniform(0, 1, size=len(households)) < self.fertility,
            self.world[age].loc[households, 'age'] >= self.move_out_age)
            # self.world[age].loc[households, 'age'] >= self.move_out_age
        # moveout = np.random.uniform(0, 1, size=moving_out) >
        moving_out_ids = self.world[age].loc[households].index[moving_out]

        self.world.events.children_move_out(moving_out_ids)
        too_old = self.world[age].loc[aging_entities, 'age'] >= self.death_age
        too_old_ids = self.world[age].loc[aging_entities].index[too_old]
        self.world.events.death(too_old_ids)

    def death(self, dying):
        self.world.remove_entities(dying)


class MoveOutSystem(System):

    stockpile_gift_fraction = 0.33333

    # TODO: what is actually the best way to handle the creation of new entities?
    #   there may be aspects of a particular type of entity which are determined
    #   independent of any single system...
    def children_move_out(self, moving_out_ids):
        gift = self.world[stockpile].loc[moving_out_ids, 'grain']\
            * self.stockpile_gift_fraction
        self.world[stockpile].loc[moving_out_ids, 'grain'] -= gift
        newdata = {position: self.world[position].loc[moving_out_ids],
                   stockpile: dict(grain=gift),
                   age: dict(age=np.zeros(gift.shape))}
        new = world.add_entities(newdata)

        self.world.events.seek_new_farmland(new)


class PlotSystem(System):

    filters = dict(households=[position, stockpile],
                   farms=[position, grain_yield])

    def __init__(self, world):
        super().__init__(world)
        fig = plt.figure()
        ax = fig.gca()
        self.fig = fig
        self.ax = ax
        im = ax.imshow(self._plot_soil_quality(), cmap='RdYlGn')
        self._plot_households()
        fig.show()
        self.fig = fig
        self.ax = ax
        self.im = im

    def _plot_households(self):
        self.scatter = self.ax.scatter(
            x=world[position].loc[self.households.ids].x,
            y=world[position].loc[self.households.ids].y,
            s=world[stockpile].loc[self.households.ids].grain
            / 1500, c='b')

    def _plot_soil_quality(self):
        data = self.world.systems[HarvestSystem].yield_mean.transpose()
        return data

    def draw(self):
        self.im.set(data=self._plot_soil_quality())
        self.scatter.remove()
        self._plot_households()
        # scatter.set_offsets(np.concatenate([x, y], axis=1))
        # scatter.set_sizes(world.components.stockpile.grain)
        self.ax.set_title(str(world.systems[YearSystem].year))
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()


# TODO: best practices for proper separatiion between systems


# some duplication here... can we just declare components as Component(name, *things/**things:type)?

world = World(position, stockpile, age, grain_yield, farmland)
world.mapsize = (80, 120)

YearSystem(world)
HarvestSystem(world)
EatingSystem(world)
MovingSystem(world)
AgeSystem(world)
MoveOutSystem(world)
PlotSystem(world)

initialize_households(world, 5)


prevt = time.time()
initt = prevt
while True:
    currt = time.time()
    world.events.update(currt - prevt)
    prevt = currt
    if np.floor(world.systems[YearSystem].year) % 1 == 0:
        world.events.draw()
        print("population:", world[position].shape[0])
        fields = np.zeros(world.mapsize)


# TODO: parameterize step size
