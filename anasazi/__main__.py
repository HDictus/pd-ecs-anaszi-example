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
    if profile:
        with cProfile.Profile() as pr:
            pyglet.app.run()
        pr.dump_stats('prof.prof')
        df = pd.DataFrame(
            pr.getstats(),
            columns=['func', 'ncalls', 'ccalls', 'tottime', 'cumtime', 'callers']
        )

        df.to_csv("profile.csv")
        return
    pyglet.app.run()

if __name__ == "__main__":
    minicli.command(display_simulation)