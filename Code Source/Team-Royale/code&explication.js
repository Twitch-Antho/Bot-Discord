Créer une chasse
Ajouter 5 indices
Inscrire les membres
Répondre aux énigmes
Afficher le classement
Donner la récompense au gagnant


------------------------------------------------------------------------
Commandes disponibles:

/halloween chasse creer
/halloween chasse ajouter-indice
/halloween chasse lancer
/halloween chasse rejoindre
/halloween chasse quitter
/halloween chasse repondre
/halloween chasse progression
/halloween chasse classement
/halloween chasse terminer
/halloween chasse annuler

Pour l’utiliser dans ton bot principal, il faudra importer le module dans ton gestionnaire de commandes :

const halloween = require('./Code Source/Team-Royale/HalloweenClueHunt');

client.commands.set(halloween.data.name, halloween);


Puis vérifier que ton système appelle bien :
await command.execute(interaction);
