"""Jouer aux dames à deux dans le terminal : chaque joueur tape son coup, comme c3 d4."""
import re

from dames import Partie, Case
from exceptions import ErreurDames


def lire_coup(texte: str) -> tuple[str, str]:
    """« c3 d4 », « c3-d4 » ou « d4xf6 » donnent ("c3", "d4"). Sinon ValueError."""

    morceaux = re.split(r"\s*(?:-|x|\s+)\s*", texte.strip())

    if len(morceaux) != 2:
        raise ValueError("tapez deux cases")

    depart, arrivee = morceaux

    try:
        depart = str(Case.depuis_nom(depart))
        arrivee = str(Case.depuis_nom(arrivee))
    except ValueError:
        raise ValueError("tapez deux cases")

    return depart, arrivee



def main() -> int:
    partie = Partie()

    print(partie.plateau)

    while partie.gagnant is None:
        try:
            texte = input(
                f"Au tour des {partie.trait}s "
                "(départ arrivée, sauver, reprendre ou quitter) : "
            )

            commande = texte.strip().lower()

            if commande == "quitter":
                print("Partie abandonnée.")
                return 0

            elif commande == "sauver":
                partie.sauvegarder("partie.json")
                print("Partie sauvegardée dans partie.json.")
                continue

            elif commande == "reprendre":
                partie = Partie.charger("partie.json")
                print("Partie reprise avec succès !")
                print(partie.plateau)
                continue

            depart, arrivee = lire_coup(texte)

            coup = partie.jouer(depart, arrivee)

            print(coup)
            print(partie.plateau)

        except FileNotFoundError:
            print("Aucune sauvegarde trouvée : partie.json n'existe pas.")

        except (ValueError, ErreurDames) as erreur:
            print(f"Refusé : {erreur}")

    if partie.gagnant == "blanc":
        print("Les blancs gagnent !")
    else:
        print("Les noirs gagnent !")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())