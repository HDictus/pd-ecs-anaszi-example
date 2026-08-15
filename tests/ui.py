from anasazi import components as comp
from anasazi import step
import pyglet


def game_window(world):
    window = pyglet.window.Window(960, 480)

    window.fps = 0
    window.selected = None


    @window.event
    def on_draw():
        window.clear()
        land = world[(comp.position, comp.grain_yield, comp.occupying_farms, comp.occupying_houses)]
        posn, yields, farms, houses = land.data()
        for i in posn.index:
            farmed = farms.loc[i, 'num occupying']
            circle = pyglet.shapes.Circle(
                x=posn.loc[i, 'x'], y=posn.loc[i, 'y'],
                radius=2, color=(0 if farmed else 255, yields.loc[i, 'mean']), 0)
            circle.draw()
        t = pyglet.text.Label(str(window.fps))
        t.draw()

    @window.event
    def update(dt):
        step(world)
        window.fps = 1/dt

    pyglet.clock.schedule_interval(update, 1/800)

    return window
