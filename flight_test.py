from simulation import Simulation
import numpy as np
import math

AU_TO_METERS = 1.496e+11
TIME_STEPS = 1000000
TIME_FACTOR = 1

def dist(pos1, pos2):
    hypt = 0.0
    hypt += (pos1.x.value - pos2.x.value) ** 2
    hypt += (pos1.y.value - pos2.y.value) ** 2
    hypt += (pos1.z.value - pos2.z.value) ** 2
    return math.sqrt(hypt) * AU_TO_METERS

arr = np.zeros((TIME_STEPS), dtype=np.float64)
sim = Simulation(time_factor=TIME_FACTOR)
ship = sim.ship
last_pos = ship.position
sim.tick(1)
for i in range(TIME_STEPS):
    sim.tick(1)
    pos = ship.position
    deltax = dist(pos, last_pos)
    last_pos = pos
    arr[i] = deltax
    print(f"{i} delta: {deltax}")
    if sim._crashed or deltax < 1e-10:
        print("Ship has crashed!")
        arr = arr[:i-1]
        break
      

print("mean:", arr.mean())
print("min:", arr.min())
print("max:", arr.max())
print("done!")