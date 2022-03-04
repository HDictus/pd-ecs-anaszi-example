from pd_ecs import World, System, Component
import numpy as np

# for now we just do farming on a random map with random changes

YEARS_PER_SECOND = 20

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
        self.yield_mean = np.random.uniform(0, 10, size=world.mapsize)
        self.yield_std = np.random.uniform(0, 20, size=world.mapsize)

    def calculate_yield(self, x, y):
        x = np.int32(np.floor(x))
        y = np.int32(np.floor(y))
        means = self.yield_mean[(x, y)]
        stds = self.yield_std[(x, y)]
        actual = np.random.normal(means, stds)
        actual[actual < 0] = 0
        return actual

    def year_passes(self):
        # TODO: this could be made better. Ideally we want to only access declared groups.
        # TODO: this is definitely an awkward way to do this. maybe system will automatically refresh after each function call?
        households = self.households()
        x = self.world.components.position.loc[households, position.x]
        y = self.world.components.position.loc[households, position.y]
        harvests = self.calculate_yield(x, y)
        self.world.components.grain_stockpile.loc[households, 'grain'] += harvests
        self.yield_mean += np.random.normal() - 0.01 * self.yield_mean
        self.yield_mean[self.yield_mean < 0] = 0
        return


class EatingSystem(System):

    households = [position, grain_stockpile]

    food_requirement = 5 * YEARS_PER_SECOND

    def update(self, dt):
        current_stockpile = self.world.components.grain_stockpile.loc[self.households(), 'grain']
        new_stockpile = current_stockpile - self.food_requirement * dt
        new_stockpile[new_stockpile < 0] = 0
        self.world.components.grain_stockpile.loc[self.households(), 'grain'] = new_stockpile

import time
import matplotlib.pyplot as plt

# TODO: this should be a sysem
def plot_world(world):
    # this may be a little confusing wrt the name v.s. the actual column...
    fig = plt.figure()
    ax = fig.gca()
    scatter = ax.scatter(x=world.components.position.x,
                         y=world.components.position.y,
                         s=world.components.grain_stockpile.grain)
    fig.show()
    return fig, ax, scatter


def update_plot(fig, ax, scatter, world):
    scatter.set_sizes(world.components.grain_stockpile.grain)
    ax.set_title(str(world.systems[YearSystem].year))
    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    return


# some duplication here... can we just declare components as Component(name, *things/**things:type)?
world = World(position=position, grain_stockpile=grain_stockpile)
world.mapsize = (100, 100)

YearSystem(world)
EatingSystem(world)
HarvestSystem(world)

initialize_households(world, 20)

f, a, s = plot_world(world)
prevt = time.time()
initt = prevt
while True:
    currt = time.time()
    world.update(currt - prevt)
    prevt = currt
    update_plot(f, a, s, world)
