import anasazi
import anasazi.components as comp
import numpy as np
import pkg_resources
import pyglet


house = pyglet.image.load(
    pkg_resources.resource_filename("anasazi", "house.png"))
#house.anchor_x = house.width//2
#house.anchor_y = 0

water = pyglet.image.load(
    pkg_resources.resource_filename("anasazi", "water.png")
)
#water.anchor_x = water.width // 2

class Window:

    def __init__(self, world, transpose=True, render_every=1):
        width, height = 1280, 960
        self.window = pyglet.window.Window(width, height)
        self.world = world
        self.i = 0
        @self.window.event
        def on_draw():
            self.i+=1 
            if self.i % render_every != 0:
                return
            self.window.clear()
            land = self.world[
                comp.POSITION + comp.YIELD]
            posn = land[comp.POSITION]
            yields = land[comp.YIELD]
            farmed_land = anasazi.farmed_land_ids(self.world)
            if transpose:
                posn[['x', 'y']] = posn[[comp.Y, comp.X]]
            maxx = posn['x'].max()
            maxy = posn['y'].max()
            ratio = min(width / maxx, height / maxy)
            yield_max = yields[comp.MEAN_YIELD].max()
            yieldcolor = ((yields[comp.MEAN_YIELD]) / yield_max) * 255
            yieldcolor[np.isnan(yieldcolor)] = 0
            patches_batch = pyglet.graphics.Batch()
            patches = []
            # TODO: can probably get large benefits from not re-initializing
            for i in posn.index:
                # TODO: num occupying, num occupants... I need to make sure these are enums or sth.
                patch = pyglet.shapes.Rectangle(
                    x=posn.loc[i, 'x'] * ratio, y=posn.loc[i, 'y'] * ratio,
                    width=ratio, height=ratio,
                    color=(0 if i in farmed_land else 255, int(yieldcolor[i]), 0),
                    batch=patches_batch)
                patches.append(patch)

            houses_batch = pyglet.graphics.Batch()
            occupancy = anasazi.home_occupancy(self.world)
            houses = self.world[comp.POSITION].to_frame().loc[occupancy.index]
            houses[comp.HOME] = occupancy
            if transpose:
                # TODO: much better to do by maintaining sprites and
                # using their positions indepenent of actual
                houses[[comp.X, comp.Y]] =\
                    houses[[comp.Y, comp.X]]
            sprites = []
            for _, row in houses.iterrows():
                sprite =pyglet.sprite.Sprite(
                    house,
                    x=row[comp.X] * ratio,
                    y=row[comp.Y] * ratio,
                    batch=houses_batch)
                sprite.scale = row[comp.HOME] / 3
                sprites.append(sprite)
            
            sources_batch = pyglet.graphics.Batch()

            sources = world[comp.POSITION + [comp.WATER_SOURCE]]
            if transpose:
                sources[[comp.X, comp.Y]] =\
                    sources[[comp.Y, comp.X]]
            for _, row in sources.iterrows():
                sprite = pyglet.sprite.Sprite(
                    water,
                    x=row[comp.X] * ratio,
                    y=row[comp.Y] * ratio,
                    batch=sources_batch
                )
                sprite.scale = 1
                sprites.append(sprite)

            patches_batch.draw()
            sources_batch.draw()
            houses_batch.draw()
            

        @self.window.event
        def update(dt):
            anasazi.step(world)
            print(world[comp.YEAR].iloc[0])


        pyglet.clock.schedule_interval(update, 1/800)
