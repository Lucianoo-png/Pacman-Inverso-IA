import pygame
from pygame.locals import *
from vector import Vector2
from constants import *
from entity import Entity
from modes import ModeController
from sprites import GhostSprites

class Ghost(Entity):
    def __init__(self, node, pacman=None, blinky=None):
        Entity.__init__(self, node)
        self.name = GHOST
        self.points = 200
        self.goal = Vector2()
        self.directionMethod = self.goalDirection
        self.pacman = pacman
        self.mode = ModeController(self)
        self.blinky = blinky
        self.homeNode = node

    def reset(self):
        Entity.reset(self)
        self.points = 200
        self.directionMethod = self.goalDirection

    def update(self, dt):
        self.sprites.update(dt)
        self.mode.update(dt)
        if self.mode.current is SCATTER:
            self.scatter()
        elif self.mode.current is CHASE:
            self.chase()
        Entity.update(self, dt)

    def scatter(self):
        self.goal = Vector2()

    def chase(self):
        self.goal = self.pacman.position

    def spawn(self):
        self.goal = self.spawnNode.position

    def setSpawnNode(self, node):
        self.spawnNode = node

    def startSpawn(self):
        self.mode.setSpawnMode()
        if self.mode.current == SPAWN:
            self.setSpeed(150)
            self.directionMethod = self.goalDirection
            self.spawn()

    def startFreight(self):
        self.mode.setFreightMode()
        if self.mode.current == FREIGHT:
            self.setSpeed(50)
            self.directionMethod = self.randomDirection

    def normalMode(self):
        self.setSpeed(100)
        self.directionMethod = self.goalDirection
        self.homeNode.denyAccess(DOWN, self)


class Blinky(Ghost):
    """
    Fantasma principal: en el Pac-Man inverso lo controla el JUGADOR con el
    teclado (Pacman_IA.txt, seccion 8: "Blinky = jugador"). Ya no usa IA de
    movimiento: solo se mueve automaticamente cuando esta en modo SPAWN
    (regresando a la casa tras ser comido con un power pellet).
    """
    def __init__(self, node, pacman=None, blinky=None):
        Ghost.__init__(self, node, pacman, blinky)
        self.name = BLINKY
        self.color = RED
        self.sprites = GhostSprites(self)

    def update(self, dt):
        self.sprites.update(dt)
        self.mode.update(dt)
        if self.mode.current is SPAWN:
            # Comido por Pac-Man con un power pellet: vuelve solo a casa
            self.spawn()
            Entity.update(self, dt)
        else:
            self.playerUpdate(dt)

    def playerUpdate(self, dt):
        self.position += self.directions[self.direction] * self.speed * dt
        direction = self.getValidKey()
        if self.overshotTarget():
            self.node = self.target
            if self.node.neighbors[PORTAL] is not None:
                self.node = self.node.neighbors[PORTAL]
            self.target = self.getNewTarget(direction)
            if self.target is not self.node:
                self.direction = direction
            else:
                self.target = self.getNewTarget(self.direction)

            if self.target is self.node:
                self.direction = STOP
            self.setPosition()
        else:
            if self.oppositeDirection(direction):
                self.reverseDirection()

    def getValidKey(self):
        key_pressed = pygame.key.get_pressed()
        if key_pressed[K_UP]:
            return UP
        if key_pressed[K_DOWN]:
            return DOWN
        if key_pressed[K_LEFT]:
            return LEFT
        if key_pressed[K_RIGHT]:
            return RIGHT
        return STOP


class Pinky(Ghost):
    """
    Fantasma aliado con IA OFENSIVA/COOPERATIVA (Pacman_IA.txt, seccion 4):
    su objetivo no es solo perseguir a Pac-Man, sino interceptarlo y
    bloquear sus rutas de escape sin estorbar al fantasma del jugador.
    """
    def __init__(self, node, pacman=None, blinky=None):
        Ghost.__init__(self, node, pacman, blinky)
        self.name = PINKY
        self.color = PINK
        self.sprites = GhostSprites(self)
        # Lista de pellets, asignada desde GameController (run.py), para
        # poder ubicar power pellets al momento de bloquear una ruta.
        self.pellets = None

    def scatter(self):
        self.goal = Vector2(TILEWIDTH*NCOLS, 0)

    def chase(self):
        # Regla: predecir hacia donde escapara Pac-Man (intercepcion),
        # en vez de ir siempre a su posicion actual.
        interceptPoint = (self.pacman.position +
                           self.pacman.directions[self.pacman.direction] * TILEWIDTH * 4)

        # Regla: si el jugador ya esta persiguiendo de cerca a Pac-Man,
        # el aliado no lo persigue por el mismo lado; intenta bloquear un
        # power pellet cercano para cerrarle esa salida de escape.
        if self.blinky is not None:
            dBlinkyPacman = (self.blinky.position - self.pacman.position).magnitudeSquared()
            if dBlinkyPacman <= (TILEWIDTH * 6) ** 2:
                blockTarget = self.nearestPowerPellet()
                if blockTarget is not None:
                    self.goal = blockTarget
                    return

        self.goal = interceptPoint

    def nearestPowerPellet(self):
        if not self.pellets:
            return None
        best = None
        bestDist = None
        for pellet in self.pellets.pelletList:
            if pellet.name == POWERPELLET:
                d = (pellet.position - self.pacman.position).magnitudeSquared()
                if bestDist is None or d < bestDist:
                    bestDist = d
                    best = pellet.position
        return best


class Inky(Ghost):
    """Fantasma opcional con IA simple (greedy): persigue usando una
    proyeccion geometrica basica, sin reglas adicionales de cooperacion."""
    def __init__(self, node, pacman=None, blinky=None):
        Ghost.__init__(self, node, pacman, blinky)
        self.name = INKY
        self.color = TEAL
        self.sprites = GhostSprites(self)

    def scatter(self):
        self.goal = Vector2(TILEWIDTH*NCOLS, TILEHEIGHT*NROWS)

    def chase(self):
        vec1 = self.pacman.position + self.pacman.directions[self.pacman.direction] * TILEWIDTH * 2
        vec2 = (vec1 - self.blinky.position) * 2
        self.goal = self.blinky.position + vec2


class Clyde(Ghost):
    """Fantasma opcional con IA simple: presiona a Pac-Man de cerca y
    se retira a su esquina cuando esta lejos (comportamiento basico)."""
    def __init__(self, node, pacman=None, blinky=None):
        Ghost.__init__(self, node, pacman, blinky)
        self.name = CLYDE
        self.color = ORANGE
        self.sprites = GhostSprites(self)

    def scatter(self):
        self.goal = Vector2(0, TILEHEIGHT*NROWS)

    def chase(self):
        d = self.pacman.position - self.position
        ds = d.magnitudeSquared()
        if ds <= (TILEWIDTH * 8)**2:
            self.scatter()
        else:
            self.goal = self.pacman.position + self.pacman.directions[self.pacman.direction] * TILEWIDTH * 4


class GhostGroup(object):
    def __init__(self, node, pacman):
        self.blinky = Blinky(node, pacman)
        self.pinky = Pinky(node, pacman, self.blinky)
        self.inky = Inky(node, pacman, self.blinky)
        self.clyde = Clyde(node, pacman)
        self.ghosts = [self.blinky, self.pinky, self.inky, self.clyde]

    def __iter__(self):
        return iter(self.ghosts)

    def update(self, dt):
        for ghost in self:
            ghost.update(dt)

    def startFreight(self):
        for ghost in self:
            ghost.startFreight()
        self.resetPoints()

    def setSpawnNode(self, node):
        for ghost in self:
            ghost.setSpawnNode(node)

    def updatePoints(self):
        for ghost in self:
            ghost.points *= 2

    def resetPoints(self):
        for ghost in self:
            ghost.points = 200

    def hide(self):
        for ghost in self:
            ghost.visible = False

    def show(self):
        for ghost in self:
            ghost.visible = True

    def reset(self):
        for ghost in self:
            ghost.reset()

    def render(self, screen):
        for ghost in self:
            ghost.render(screen)
