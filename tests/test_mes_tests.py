
import json

from dames import Partie
from main import main


def test_commande_sauver(monkeypatch, tmp_path):
    # On travaille dans un dossier temporaire
    monkeypatch.chdir(tmp_path)

    # L'utilisateur demande de sauvegarder puis de quitter
    commandes = iter(["sauver", "quitter"])
    monkeypatch.setattr("builtins.input", lambda _: next(commandes))

    main()

    # Vérifier que le fichier a été créé
    fichier = tmp_path / "partie.json"
    assert fichier.exists()

    # Vérifier son contenu
    donnees = json.loads(fichier.read_text(encoding="utf-8"))

    assert donnees["trait"] == "blanc"
    assert len(donnees["pieces"]) == 40


def test_commande_reprendre(monkeypatch, tmp_path, capsys):
    # Préparer une partie sauvegardée
    monkeypatch.chdir(tmp_path)

    partie = Partie()
    partie.jouer("d4", "e5")
    partie.sauvegarder("partie.json")

    # L'utilisateur demande de reprendre puis de quitter
    commandes = iter(["reprendre", "quitter"])
    monkeypatch.setattr("builtins.input", lambda _: next(commandes))

    main()

    # Vérifier que la reprise a réussi
    sortie = capsys.readouterr().out

    assert "Partie reprise avec succès !" in sortie
    assert "P" in sortie
