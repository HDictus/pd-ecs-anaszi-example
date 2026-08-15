from pd_ecs import World
import anasazi
import pyglet
import cProfile
import pandas as pd
import minicli


def display_simulation(profile=False, render_every: int=1):
    world = World()

    anasazi.initialize(world)
    win = anasazi.ui.Window(world, render_every=render_every)
    pyglet.app.run()

if __name__ == "__main__":
    minicli.command(display_simulation)
