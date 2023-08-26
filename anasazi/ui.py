import anasazi
import anasazi.components as comp
import numpy as np
import pkg_resources
import pyglet


house = pyglet.image.load(
    pkg_resources.resource_filename("anasazi", "house.png"))
house.anchor_x = house.width//2
house.anchor_y = 0


class Window:

    def __init__(self, world, transpose=True):
        width, height = 960, 480
        self.window = pyglet.window.Window(width, height)
        self.world = world

        @self.window.event
        def on_draw():
            self.window.clear()
            land = self.world[
                [comp.POSITION, comp.YIELD]]
            posn = land[comp.POSITION]
            yields = land[comp.YIELD]
            farmed_land = self.world[comp.FARMED]
            if transpose:
                posn[['x', 'y']] = posn[['y', 'x']]
            maxx = posn['x'].max()
            maxy = posn['y'].max()
            ratio = min(width / maxx, height / maxy)
            yield_max = yields['mean'].max()
            yieldcolor = ((yields['mean']) / yield_max) * 255
            yieldcolor[np.isnan(yieldcolor)] = 0
            patches_batch = pyglet.graphics.Batch()
            patches = []
            for i in posn.index:
                # TODO: num occupying, num occupants... I need to make sure these are enums or sth.
                patch = pyglet.shapes.Rectangle(
                    x=posn.loc[i, 'x'] * ratio, y=posn.loc[i, 'y'] * ratio,
                    width=ratio, height=ratio,
                    color=(0 if i in farmed_land.index else 255, int(yieldcolor[i]), 0),
                    batch=patches_batch)
                patches.append(patch)

            houses_batch = pyglet.graphics.Batch()
            houses = world[[comp.POSITION, comp.OCCUPYING_HOMES.num]]
            if transpose:
                # TODO: much better to do by maintaining sprites and 
                # using their positions indepenent of actual
                houses[[comp.POSITION.x, comp.POSITION.y]] =\
                    houses[[comp.POSITION.y, comp.POSITION.x]]
            sprites = []
            for _, row in houses.iterrows():
                sprite =pyglet.sprite.Sprite(
                    house, 
                    x=row[comp.POSITION.x] * ratio,
                    y=row[comp.POSITION.y] * ratio,
                    batch=houses_batch)
                sprite.scale = row[comp.OCCUPYING_HOMES.num] / 3
                sprites.append(sprite)
                
            patches_batch.draw()
            houses_batch.draw()
                

        @self.window.event
        def update(dt):
            anasazi.step(world)
            print(world[comp.TIME]['year'].iloc[0])


        pyglet.clock.schedule_interval(update, 1/800)
