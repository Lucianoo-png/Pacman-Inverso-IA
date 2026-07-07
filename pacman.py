import pygame
from pygame.locals import *
from vector import Vector2
from constants import *
from entity import Entity
from sprites import PacmanSprites

class Pacman(Entity):
    """
    Pac-Man "inverso": ya NO se controla con el teclado.
    Ahora es una IA DEFENSIVA (ver Pacman_IA.txt, secciones 3 y 6) cuyo
    objetivo es sobrevivir: evita a los fantasmas, come pellets cuando es
    seguro y busca power pellets cuando está en peligro.

    Modelo usado (igual al de las reglas del documento):
        hechos del juego -> reglas de decision -> puntaje de cada ruta -> movimiento
    """

    def __init__(self, node):
        Entity.__init__(self, node)
        self.name = PACMAN
        self.color = YELLOW
        self.direction = LEFT
        self.setBetweenNodes(LEFT)
        self.alive = True
        self.sprites = PacmanSprites(self)

        # La IA decide la direccion en cada interseccion (igual que un fantasma)
        self.directionMethod = self.decidirDireccionIA

        # "Hechos del juego" que la IA necesita. Se asignan desde
        # GameController (run.py) una vez que existen fantasmas y pellets.
        self.ghosts = None
        self.pellets = None

        # Distancias (en pixeles) que definen cuando algo se considera "cerca"
        self.dangerRadius = TILEWIDTH * 5
        self.pelletRadius = TILEWIDTH * 3
        self.powerPelletRadius = TILEWIDTH * 6

    def reset(self):
        Entity.reset(self)
        self.direction = LEFT
        self.setBetweenNodes(LEFT)
        self.alive = True
        self.image = self.sprites.getStartImage()
        self.sprites.reset()

    def die(self):
        self.alive = False
        self.direction = STOP

    def update(self, dt):
        self.sprites.update(dt)
        # Se mueve igual que cualquier entidad basada en nodos: en cada
        # interseccion, la IA (decidirDireccionIA) elige hacia donde ir.
        Entity.update(self, dt)

    # ------------------------------------------------------------------
    # IA de escape: motor de inferencia basado en reglas (Pacman_IA.txt)
    # ------------------------------------------------------------------
    def decidirDireccionIA(self, directions):
        """
        Evalua cada direccion valida con un puntaje y elige la mejor
        (equivalente al "motor de inferencia" descrito en el documento:
        analiza reglas, selecciona las aplicables y ejecuta la mejor accion).
        """
        mejorPuntaje = None
        mejorDireccion = directions[0]
        for direction in directions:
            nextNode = self.node.neighbors[direction]
            puntaje = self.evaluarRuta(nextNode)
            if mejorPuntaje is None or puntaje > mejorPuntaje:
                mejorPuntaje = puntaje
                mejorDireccion = direction
        return mejorDireccion

    def evaluarRuta(self, node):
        """
        Puntaje de una ruta =
            + pellets cercanos
            + power pellet cercano (solo si hay peligro)
            - cercania del fantasma del jugador (Blinky)
            - cercania del fantasma aliado (Pinky)
            - callejon sin salida
            + numero de salidas disponibles
        """
        score = 0
        pos = node.position

        # SI no hay peligro ENTONCES buscar el pellet mas cercano
        if self.pellets is not None:
            for pellet in self.pellets.pelletList:
                if pellet.name != PELLET:
                    continue
                d = (pellet.position - pos).magnitudeSquared()
                if d <= self.pelletRadius ** 2:
                    score += 5

        # SI el fantasma del jugador (o el aliado) esta cerca ENTONCES huir
        peligro = False
        if self.ghosts is not None:
            for ghost in self.ghosts:
                if ghost.mode.current == FREIGHT or ghost.mode.current == SPAWN:
                    # Un fantasma asustado o regresando a casa no es peligro
                    continue
                d = (ghost.position - pos).magnitudeSquared()
                if d <= self.dangerRadius ** 2:
                    peligro = True
                    if ghost.name == BLINKY:
                        score -= 80          # fantasma del jugador: mayor riesgo
                    elif ghost.name == PINKY:
                        score -= 60          # fantasma aliado
                    else:
                        score -= 40          # fantasmas opcionales

        # SI hay power pellet cerca Y un fantasma esta cerca ENTONCES ir al power pellet
        if peligro and self.pellets is not None:
            for pellet in self.pellets.pelletList:
                if pellet.name == POWERPELLET:
                    d = (pellet.position - pos).magnitudeSquared()
                    if d <= self.powerPelletRadius ** 2:
                        score += 100

        # SI no hay salida (callejon sin salida) ENTONCES es una mala ruta
        salidas = 0
        for exitDir in [UP, DOWN, LEFT, RIGHT]:
            if node.neighbors[exitDir] is not None and self.name in node.access[exitDir]:
                salidas += 1
        if salidas <= 1:
            score -= 50
        else:
            score += salidas * 5

        return score

    def eatPellets(self, pelletList):
        for pellet in pelletList:
            if self.collideCheck(pellet):
                return pellet
        return None

    def collideGhost(self, ghost):
        return self.collideCheck(ghost)

    def collideCheck(self, other):
        d = self.position - other.position
        dSquared = d.magnitudeSquared()
        rSquared = (self.collideRadius + other.collideRadius)**2
        if dSquared <= rSquared:
            return True
        return False
