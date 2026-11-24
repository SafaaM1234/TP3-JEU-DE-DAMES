"""Le jeu de dames en objets : cases, pièces, plateau et partie.

Règles du jeu de dames international (plateau de 10 x 10), simplifiées : une seule prise par
coup (pas de rafle) et pas de règle de la majorité.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from exceptions import CoupInvalideError

COLONNES = "abcdefghij"
TAILLE = 10
DIAGONALES = [(1, 1), (-1, 1), (1, -1), (-1, -1)]


def adversaire(couleur: str) -> str:
    """La couleur de l'autre joueur."""
    return "noir" if couleur == "blanc" else "blanc"


# --- Étape 1 : la case ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Case:
    """Une case, de a1 à j10. Immuable : on peut la hacher et s'en servir comme clé."""

    colonne: str
    ligne: int

    def __post_init__(self):
        
        if not isinstance(self.colonne, str) or len(self.colonne) != 1 or self.colonne not in COLONNES:
            raise ValueError("colonne invalide")

        if not isinstance(self.ligne, int) or isinstance(self.ligne, bool) or not 1 <= self.ligne <= 10:
            raise ValueError("ligne invalide")

    @classmethod
    def depuis_nom(cls, nom: str) -> "Case":
        """Case.depuis_nom("c3") donne Case('c', 3) ; un nom mal formé lève ValueError."""

        if not isinstance(nom, str) or len(nom) not in (2, 3):
            raise ValueError("nom de case invalide")
        
        colonne = nom[0]
        numero = nom[1:]

        if colonne not in COLONNES or not numero.isdigit():
            raise ValueError("nom de case invalide")

        try:
            return cls(colonne, int(numero))
        except ValueError:
            raise ValueError("nom de case invalide")

    @property
    def est_noire(self) -> bool:
        """On ne joue que sur les cases noires ; a1 est noire."""

        return (COLONNES.index(self.colonne) + self.ligne) % 2 == 1

    def decaler(self, dc: int, dl: int) -> "Case | None":
        """La case située dc colonnes et dl lignes plus loin, ou None si on sort du plateau."""

        nouvelle_colonne = COLONNES.index(self.colonne) + dc
        nouvelle_ligne = self.ligne + dl

        if not (0 <= nouvelle_colonne < TAILLE and 1 <= nouvelle_ligne <= TAILLE):
            return None

        return Case(COLONNES[nouvelle_colonne], nouvelle_ligne)

    def __str__(self) -> str:
        return f"{self.colonne}{self.ligne}"



def en_case(valeur: "Case | str") -> Case:
    """Accepte une Case ou un nom comme "c3"."""
    return valeur if isinstance(valeur, Case) else Case.depuis_nom(valeur)


def ordre(case: Case) -> tuple[int, int]:
    """Clé de tri : ligne par ligne, puis de gauche à droite."""
    return case.ligne, COLONNES.index(case.colonne)


# --- Étape 2 : les pièces ------------------------------------------------------------------------
class Piece(ABC):
    """Une pièce : une couleur qui ne change jamais. Elle ne connaît pas sa case :
    c'est le plateau qui sait où sont les pièces."""

    COULEURS = ("blanc", "noir")
    LETTRE = "?"          # redéfinis par chaque sous-classe
    NOM = "pièce"
    FEMININ = False

    def __init__(self, couleur: str):
        if couleur not in self.COULEURS:
            raise ValueError("couleur invalide")

        self._couleur = couleur

    @property
    def couleur(self) -> str:
        return self._couleur

    @property
    def sens(self) -> int:
        return 1 if self.couleur == "blanc" else -1

    @property
    def symbole(self) -> str:
        return self.LETTRE.upper() if self.couleur == "blanc" else self.LETTRE.lower()

    def est_adverse(self, autre: "Piece | None") -> bool:
        return autre is not None and self.couleur != autre.couleur

    @abstractmethod
    def deplacements(self, case: Case, plateau: "Plateau") -> set[Case]:
        pass

    @abstractmethod
    def prises(self, case: Case, plateau: "Plateau") -> dict[Case, Case]:
        pass

    def promouvoir(self, case: Case) -> "Piece":
        return self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.couleur!r})"

    
    def __str__(self) -> str:
        adjectif = self.couleur

        if self.FEMININ:
            adjectif += "he" if self.couleur == "blanc" else "e"

        return f"{self.NOM} {adjectif}"


# --- Étape 3 : le plateau ------------------------------------------------------------------------
class Plateau:
    """Le plateau A des pièces (composition), rangées dans un dict privé case -> pièce."""

    def __init__(self):
        self._pieces: dict[Case, Piece] = {}

    @classmethod
    def depuis_dict(cls, pieces: dict[str, str]) -> "Plateau":
        """Constructeur alternatif : Plateau.depuis_dict({"c3": "P", "f6": "d"}).
        P = pion, D = dame ; majuscule pour les blancs, minuscule pour les noirs."""
        plateau = cls()
        for nom, lettre in pieces.items():
            couleur = "blanc" if lettre.isupper() else "noir"
            classe = Pion if lettre.upper() == "P" else Dame
            plateau.placer(nom, classe(couleur))
        return plateau

    @classmethod
    def position_initiale(cls) -> "Plateau":
        plateau = cls()

        for ligne in range(1, 11):

            if ligne <= 4:
                couleur = "blanc"
            elif ligne >= 7:
                couleur = "noir"
            else:
                continue

            for colonne in COLONNES:
                case = Case(colonne, ligne)

                if case.est_noire:
                    plateau.placer(case, Pion(couleur))

        return plateau

    def placer(self, case: "Case | str", piece: Piece) -> None:
        case = en_case(case)

        if not case.est_noire:
            raise ValueError("case blanche")

        if case in self._pieces:
            raise ValueError("case déjà occupée")

        self._pieces[case] = piece

    def __getitem__(self, case: "Case | str") -> "Piece | None":
        case = en_case(case)
        return self._pieces.get(case)

    def __contains__(self, case: "Case | str") -> bool:
        case = en_case(case)
        return case in self._pieces

    def __len__(self) -> int:
        return len(self._pieces)

    def __iter__(self):
        """Parcourt les cases occupées, ligne par ligne, de gauche à droite."""
        return iter(sorted(self._pieces, key=ordre))

    def compter(self, couleur: str) -> int:
        return sum(1 for case in self if self[case].couleur == couleur)

    # --- Étape 6
    def prises_possibles(self, couleur: str) -> dict[Case, dict[Case, Case]]:
        """Toutes les prises d'un joueur : {départ: {arrivée: pièce prise}}, seulement pour les
        pièces qui peuvent prendre."""
        resultat = {}

        for case in self:
            piece = self[case]

            if piece.couleur == couleur:
                prises = piece.prises(case, self)

                if prises:
                    resultat[case] = prises

        return resultat

    def coups_possibles(self, couleur: str) -> list[tuple[Case, Case]]:
        """Les coups autorisés, triés. S'il existe des prises, seules les prises comptent."""

        prises = self.prises_possibles(couleur)
        resultat = []

        # Si une prise existe, les déplacements simples sont interdits.
        if prises:
            for depart, destinations in prises.items():
                for arrivee in destinations:
                    resultat.append((depart, arrivee))

        else:
            for depart in self:
                piece = self[depart]

                if piece.couleur == couleur:
                    for arrivee in piece.deplacements(depart, self):
                        resultat.append((depart, arrivee))

        return sorted(resultat, key=lambda coup: (ordre(coup[0]), ordre(coup[1])))

    def deplacer(self, depart: "Case | str", arrivee: "Case | str") -> "Piece | None":
        """Joue un coup, renvoie la pièce prise ou None. Vérifier d'abord, modifier ensuite."""
        depart = en_case(depart)
        arrivee = en_case(arrivee)

        piece = self[depart]

        if piece is None:
            raise CoupInvalideError(depart, arrivee,"aucune pièce sur la case de départ")

        couleur = piece.couleur
        prises = self.prises_possibles(couleur)

        piece_prise = None

        if prises:
            if depart not in prises or arrivee not in prises[depart]:
                raise CoupInvalideError(depart, arrivee, "la prise est obligatoire")

            case_prise = prises[depart][arrivee]
            piece_prise = self[case_prise]

        else:
            if arrivee not in piece.deplacements(depart, self):
                raise CoupInvalideError(depart, arrivee, "déplacement interdit")

        # Modifier le plateau seulement après les vérifications.
        del self._pieces[depart]

        if piece_prise is not None:
            del self._pieces[case_prise]

        self._pieces[arrivee] = piece.promouvoir(arrivee)

        return piece_prise

    # --- Étape 8
    def vers_dict(self) -> dict[str, str]:
        """L'inverse de depuis_dict : {"c3": "P", "f6": "d", ...}, dans l'ordre du plateau."""
        return {
        str(case): self[case].symbole
        for case in self
        }
    
    # --- Affichage (fourni)
    def __repr__(self) -> str:
        return f"<Plateau : {self.compter('blanc')} blancs, {self.compter('noir')} noirs>"

    def __str__(self) -> str:
        lignes = []
        for ligne in range(TAILLE, 0, -1):
            cases = []
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                piece = self[case]
                cases.append(piece.symbole if piece else "." if case.est_noire else " ")
            lignes.append(f"{ligne:>2}  " + " ".join(cases))
        lignes.append("    " + " ".join(COLONNES))
        return "\n".join(lignes)


# --- Étape 4 : le pion ---------------------------------------------------------------------------
class Pion(Piece):
    LETTRE = "P"
    NOM = "pion"

    def deplacements(self, case, plateau):
        """Une case en diagonale, vers l'avant, si elle est libre."""
        case = en_case(case)
        resultat = set()

        for dc in (-1, 1):
            destination = case.decaler(dc, self.sens)

            if destination is not None and plateau[destination] is None:
                resultat.add(destination)

        return resultat
    
    def prises(self, case, plateau):
        """Sauter une pièce adverse voisine (avant ou arrière) vers la case libre derrière."""
        case = en_case(case)
        resultat = {}

        for dc, dl in DIAGONALES:
            voisine = case.decaler(dc, dl)
            arrivee = case.decaler(2 * dc, 2 * dl)

            if voisine is None or arrivee is None:
                continue

            piece_voisine = plateau[voisine]

            if self.est_adverse(piece_voisine) and plateau[arrivee] is None:
                resultat[arrivee] = voisine

        return resultat

    # --- Étape 6
    def promouvoir(self, case):
        """Sur la dernière ligne (10 pour les blancs, 1 pour les noirs), le pion devient dame."""
        case = en_case(case)

        if self.couleur == "blanc" and case.ligne == 10:
            return Dame("blanc")

        if self.couleur == "noir" and case.ligne == 1:
            return Dame("noir")

        return self

# --- Étape 5 : la dame ---------------------------------------------------------------------------
class Dame(Piece):
    LETTRE = "D"
    NOM = "dame"
    FEMININ = True

    def deplacements(self, case, plateau):
        """La dame se déplace sur toutes les cases libres en diagonale."""
        case = en_case(case)
        resultat = set()

        for dc, dl in DIAGONALES:
            destination = case.decaler(dc, dl)

            while destination is not None and plateau[destination] is None:
                resultat.add(destination)
                destination = destination.decaler(dc, dl)

        return resultat

    def prises(self, case, plateau):
        """La dame capture une pièce adverse et peut atterrir sur toute case libre derrière."""
        case = en_case(case)
        resultat = {}

        for dc, dl in DIAGONALES:
            destination = case.decaler(dc, dl)

            # Chercher une pièce sur la diagonale.
            while destination is not None and plateau[destination] is None:
                destination = destination.decaler(dc, dl)

            if destination is None:
                continue

            piece = plateau[destination]

            # Une pièce de notre couleur bloque le passage.
            if not self.est_adverse(piece):
                continue

            case_prise = destination
            arrivee = case_prise.decaler(dc, dl)

            # Toutes les cases libres derrière la pièce sont des destinations possibles.
            while arrivee is not None and plateau[arrivee] is None:
                resultat[arrivee] = case_prise
                arrivee = arrivee.decaler(dc, dl)

        return resultat


# --- Étape 7 : la partie -------------------------------------------------------------------------
@dataclass(frozen=True)
class Coup:
    """Un coup joué. Gelé : un coup joué ne change plus."""
    numero: int
    couleur: str
    depart: str
    arrivee: str
    prise: bool = False

    def __str__(self) -> str:
        """Notation des dames : "1. c3-d4" pour un déplacement, "4. d4xf6" pour une prise."""
        symbole = "x" if self.prise else "-"
        return f"{self.numero}. {self.depart}{symbole}{self.arrivee}"


class Partie:
    """Une partie A un plateau et un historique (composition) et sait à qui c'est le tour."""

    def __init__(self, plateau: "Plateau | None" = None):
        self.plateau = plateau if plateau is not None else Plateau.position_initiale()
        self.trait = "blanc"                  # la couleur qui doit jouer
        self.historique: list[Coup] = []

    def jouer(self, depart: str, arrivee: str) -> Coup:
        """Vérifie le trait, joue, note le coup, passe la main à l'adversaire."""

        depart = en_case(depart)
        arrivee = en_case(arrivee)

        piece = self.plateau[depart]

        if piece is None:
            raise CoupInvalideError(depart, arrivee, "aucune pièce sur la case de départ")

        if piece.couleur != self.trait:
            raise CoupInvalideError(depart,arrivee, f"c'est aux {self.trait}s de jouer")
        
        couleur = self.trait

        piece_prise = self.plateau.deplacer(depart, arrivee)

        numero = len(self.historique) + 1

        coup = Coup(
            numero,
            couleur,
            str(depart),
            str(arrivee),
            piece_prise is not None
        )

        self.historique.append(coup)

        self.trait = adversaire(self.trait)

        return coup

    @property
    def gagnant(self) -> "str | None":
        """Celui qui a le trait et ne peut plus jouer a perdu : la couleur gagnante, ou None."""
        if self.plateau.coups_possibles(self.trait):
            return None

        return adversaire(self.trait)

    # --- Étape 8
    def sauvegarder(self, chemin) -> None:
        """Écrit la partie en JSON : {"trait": ..., "pieces": {"c3": "P", ...}}."""
        donnees = {
            "trait": self.trait,
            "pieces": self.plateau.vers_dict()
        }

        with open(chemin, "w", encoding="utf-8") as fichier:
            json.dump(donnees, fichier, ensure_ascii=False, indent=2)

    @classmethod
    def charger(cls, chemin) -> "Partie":
        """Constructeur alternatif : recrée une partie écrite par sauvegarder."""
        with open(chemin, "r", encoding="utf-8") as fichier:
            donnees = json.load(fichier)

        plateau = Plateau.depuis_dict(donnees["pieces"])

        partie = cls(plateau)
        partie.trait = donnees["trait"]

        return partie