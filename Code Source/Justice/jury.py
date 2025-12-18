import random

def select_jury(members, accused_id, size):
    eligible = [m for m in members if m.id != accused_id and not m.bot]
    return random.sample(eligible, min(size, len(eligible)))
