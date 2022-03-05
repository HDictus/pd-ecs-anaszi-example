from pd_ecs import World, System, Component
import numpy as np
from scipy.ndimage import gaussian_filter

# for now we just do farming on a random map with random changes

YEARS_PER_SECOND = 2

# TODO: better as kwargs name: type?
position = Component("x", "y")
grain_stockpile = Component("grain")


def initialize_households(world, n_households, initial_grain=20):
    x = np.random.choice(range(world.mapsize[0]), n_households, replace=False)
    y = np.random.choice(range(world.mapsize[1]), n_households, replace=False)
    grain = np.ones((n_households, )) * initial_grain
    world.add_entities(position=dict(x=x, y=y), grain_stockpile=dict(grain=grain))
    return


class YearSystem(System):
    time = 0
    seconds_to_years = YEARS_PER_SECOND

    @property
    def year(self):
        return self.time * self.seconds_to_years

    def update(self, dt):
        yearbefore = int(np.floor(self.year))
        self.time += dt
        yearafter = int(np.floor(self.year))
        for i in range(yearafter - yearbefore):
            self.world.events.year_passes()


class HarvestSystem(System):

    households = [position, grain_stockpile]

    def __init__(self, world):
        super().__init__(world)
        self.yield_mean = np.random.uniform(0, 15, size=world.mapsize)
        self.yield_mean = gaussian_filter(self.yield_mean, sigma=2)
        self.yield_std = np.random.uniform(0, 5, size=world.mapsize)

    def calculate_yield(self, x, y):
        x = np.int32(np.floor(x))
        y = np.int32(np.floor(y))
        means = self.yield_mean[(x, y)]
        stds = self.yield_std[(x, y)]
        actual = np.random.normal(means, stds)
        actual[actual < 0] = 0
        return actual

    def mutate_yield(self):
        self.yield_mean += np.random.normal(size=self.yield_mean.shape, scale=0.5)
        normalized_yield = self.yield_mean - self.yield_mean.mean()
        # self.yield_mean = gaussian_filter(self.yield_mean, sigma=0.01)
        self.yield_mean += (
            0.05 * gaussian_filter(normalized_yield, sigma=0.75)
            - 0.01 * normalized_yield**2)
        self.yield_mean[self.yield_mean < 0] = 0

    def year_passes(self):
        # TODO: this could be made better. Ideally we want to only access declared groups.
        # TODO: this is definitely an awkward way to do this. maybe system will automatically refresh after each function call?
        households = self.households()
        x = self.world.components.position.loc[households, position.x]
        y = self.world.components.position.loc[households, position.y]
        harvests = self.calculate_yield(x, y)
        self.world.events.harvest(harvests)
        self.mutate_yield()

    def harvest(self, harvests):
        households = self.households()
        self.world.components.grain_stockpile.loc[households, 'grain'] +=\
            harvests
        return


class MovingSystem(System):

    # TODO: can have a maximum distance traveled to keep efficient
    households = [position, grain_stockpile]

    def harvest(self, harvest):
        households = self.households()
        need = self.world.systems[EatingSystem].yearly_consumption
        expectation = harvest
        stockpile = self.world.components.grain_stockpile.loc[households, 'grain']
        harvest_needed = need - stockpile
        moving = expectation < harvest_needed
        moving_households = households[moving]
        yieldmeans = self.world.systems[HarvestSystem].yield_mean
        unoccupied_yields = yieldmeans.copy()
        unoccupied_yields[self.occupation] = -np.inf

        for harvest_needed, household in zip(
                harvest_needed[moving], moving_households):
            adequate_squares = unoccupied_yields > harvest_needed
            if adequate_squares.any():
                posns = np.transpose(np.nonzero(adequate_squares))
                # TODO: bit of a long way to get components...
                #   ideally we wouldn't need to.
                oldposition = self.world.components.position.loc[household, ['x', 'y']].values
                dists = np.linalg.norm(np.float32(posns - oldposition), axis=1)
                nearest_posn = posns[np.argmin(dists)]
                self.world.components.position.loc[household, ['x', 'y']] = nearest_posn
                unoccupied_yields[tuple(oldposition)] = yieldmeans[tuple(oldposition)]
                unoccupied_yields[tuple(nearest_posn)] = -np.inf

    @property
    def occupation(self):
        occu = np.zeros(self.world.mapsize, dtype=bool)
        positions = self.world.components.position.loc[self.households()]
        occu[(np.int32(positions['x']), np.int32(positions['y']))] = True
        return occu


class EatingSystem(System):

    households = [position, grain_stockpile]

    yearly_consumption = 15

    def update(self, dt):
        current_stockpile = self.world.components.grain_stockpile.loc[self.households(), 'grain']
        new_stockpile = current_stockpile - self.yearly_consumption * (dt * YEARS_PER_SECOND)
        new_stockpile[new_stockpile < 0] = 0
        self.world.components.grain_stockpile.loc[self.households(), 'grain'] = new_stockpile

import time
import matplotlib.pyplot as plt


# def scatter_posns(x, y):
#     return -y, x

# TODO: this should be a sysem
def plot_world(world):
    # this may be a little confusing wrt the name v.s. the actual column...
    fig = plt.figure()
    ax = fig.gca()
    im = ax.imshow(world.systems[HarvestSystem].yield_mean.transpose(), cmap='RdYlGn',
                   clim=[0, 10])
    scatter = ax.scatter(x=world.components.position.x,
                         y=world.components.position.y,
                         s=world.components.grain_stockpile.grain)
    fig.show()
    return fig, ax, scatter, im


def update_plot(fig, ax, scatter, im, world):
    # TODO: we can be more efficient by updating imshow only each year, by making this a system
    im.set(data=world.systems[HarvestSystem].yield_mean.transpose())
    scatter.remove()
    scatter = ax.scatter(x=world.components.position.x,
                         y=world.components.position.y,
                         s=world.components.grain_stockpile.grain,
                         c='b')
    # scatter.set_offsets(np.concatenate([x, y], axis=1))
    # scatter.set_sizes(world.components.grain_stockpile.grain)
    ax.set_title(str(world.systems[YearSystem].year))
    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    return fig, ax, scatter, im


# some duplication here... can we just declare components as Component(name, *things/**things:type)?
world = World(position=position, grain_stockpile=grain_stockpile)
world.mapsize = (100, 100)

YearSystem(world)
EatingSystem(world)
HarvestSystem(world)
MovingSystem(world)

initialize_households(world, 20)

plotinfo = plot_world(world)
prevt = time.time()
initt = prevt
while True:
    currt = time.time()
    world.update(currt - prevt)
    prevt = currt
    plotinfo = update_plot(*plotinfo, world)
