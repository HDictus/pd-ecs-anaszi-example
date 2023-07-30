from pd_ecs import World
import time
import anasazi
import anasazi.components as comp
import numpy as np
import pyglet
import matplotlib.pyplot as plt

world = World()

anasazi.initialize(world)
win = anasazi.ui.Window(world)
pyglet.app.run()
