from pd_ecs import World, System
import time
from anasazi import (
    comps,
    HarvestSystem,
    EatingSystem,
    MovingSystem,
    position,
    stockpile,
    grain_yield,
    food_needs,
    occupying_houses,
    YearSystem
)
import numpy as np
import pyglet
import matplotlib.pyplot as plt


world = World(*comps)
HarvestSystem(world)
EatingSystem(world)
MovingSystem(world)
yrsys = YearSystem(world)


class Window:

    def __init__(self, world):
        self.window = pyglet.window.Window(960, 480)
        self.world = world

        @self.window.event
        def on_draw():
            self.world.events.draw(self.window)
            return

        @self.window.event
        def on_mouse_press(x, y, button, mod):
            self.world.events.mouse_pressed(x, y, button)
            return

        @self.window.event
        def on_mouse_release(x, y, button, mod):
            self.world.events.mouse_released(x, y, button)
            return

        @self.window.event
        def update(dt):
            self.world.events.update(dt)
            return

        pyglet.clock.schedule_interval(update, 1/800)


class Renderer(System):

    filters = dict(land=[position, grain_yield],
                   homes=[position, occupying_houses])

    def draw(self, window):
        scale = 3
        window.clear()
        posns, yields = self.land.data()
        maxg = yields['mean'].max()
        for x, y, c in zip(posns.x, posns.y, yields['mean']):
            pyglet.shapes.Circle(x=x*scale, y=y*scale, radius=scale,
                                 color=(0, int(np.floor(c / maxg * 255)), 0)).draw()
        posns, nums = self.homes.data()
        for x, y, sz in zip(posns.x, posns.y, nums['num occupants']):
            if sz > 0:
                pyglet.shapes.Circle(x=x*scale, y=y*scale, radius=sz,
                                     color=(255, 255, 255)).draw()
        t = pyglet.text.Label(str(yrsys.intyear))
        t.draw()


Renderer(world)
hhlds = world.add_entities({position: {'x': range(100), 'y': range(100)},
                            food_needs: {'grain': 1}})
world.events.find_home(hhlds)
win = Window(world)
pyglet.app.run()
