import anasazi
import anasazi.components as comp
import numpy as np
import pyglet


class Window:

    def __init__(self, world):
        width, height = 960, 480
        self.window = pyglet.window.Window(width, height)
        self.world = world

        @self.window.event
        def on_draw():
            self.window.clear()
            land = self.world[
                [comp.POSITION, comp.YIELD,
                 comp.OCCUPYING_HOMES]]
            posn = land[comp.POSITION]
            yields = land[comp.YIELD]
            houses = land[comp.OCCUPYING_HOMES]
            farmed_land = self.world[
                [comp.POSITION, comp.YIELD, comp.FARMED]
            ]
            maxx = posn['x'].max()
            maxy = posn['y'].max()
            ratio = min(width / maxx, height / maxy)
            yield_max = yields['mean'].max()
            yieldcolor = ((yields['mean']) / yield_max) * 255
            yieldcolor[np.isnan(yieldcolor)] = 0
            for i in posn.index:
                # TODO: num occupying, num occupants... I need to make sure these are enums or sth.
                circle = pyglet.shapes.Circle(
                    x=posn.loc[i, 'x'] * ratio, y=posn.loc[i, 'y'] * ratio,
                    radius=2, color=(0 if i in farmed_land.index else 255, int(yieldcolor[i]), 0))
                circle.draw()

        @self.window.event
        def update(dt):
            anasazi.step(world)
            print(world[comp.TIME]['year'].iloc[0])


        pyglet.clock.schedule_interval(update, 1/800)
