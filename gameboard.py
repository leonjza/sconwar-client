from entities import Entities


class GameBoard(object):
    y: int
    x: int
    entities: []

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.entities = []

    def add_entity(self, entity: Entities, x: int, y: int):
        self.entities.append((entity.value, x, y))

    def get_entity(self, x: int, y: int) -> (int, int, int):
        for entity in self.entities:
            e, ex, ey = entity
            if ex == x and ey == y:
                return entity

        return None, None, None

    @staticmethod
    def box(v):
        if v == "None":
            return f'[ ]'

        return f'[{v}]'

    def draw(self):
        print(self.draw_str())

    def draw_str(self) -> str:
        a = "\n"
        for y in reversed(range(1, self.y + 1)):
            a += f'{y:2}'
            for x in range(1, self.x + 1):
                t, ex, ey = self.get_entity(x, y)
                a += self.box(f'{t}')
            a += "\n"

        # bottom ruler
        a += f'{1:4}'
        for x in range(2, self.x + 1):
            a += f'{x:3}'
        a += "\n"

        return a
