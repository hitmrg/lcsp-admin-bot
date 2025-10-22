# lcsp-admin-bot

## Bot discord, gestion administrative lcsp (laboratoire cybersécurité supinfo paris)

### Commandes disponibles:

👑 = Nécessite rôle Administrateur pour exécuter la commande
👤 = Ne nécessite aucun rôle pour exécuter la commande

**Admin:**

- ✅👑`/setup` - Initialiser le serveur (création des rôles, des channels, etc)
- ✅👑`/announce [titre] [section1] [description1] [section2] [description2] [section3] [description3] [couleur] [ping_role] [image_url][footer]` - Faire une annonce structurée
- ✅👑`/announce_simple [titre] [message] [ping] ` - Faire une annonce simple
- ✅👑`/clear [nombre] [user]` - Supprimer une grande quantité de message dans un channel
- ✅👑`/info` - Obtenir des informations sur le serveur

**Membres:**

- ✅👑`/membre_add [user] [nom] [pole] [email] [spécialisation]` - Ajouter un membre
- ✅👤`/membre_info [user]` - Voir les infos
- ✅👑`/membre_update [user] [nom] [pole] [email] [spécialisation] [statut]` - Modifier un membre
- ✅👑`/membre_delete [user]` - Supprimer un membre
- ✅👤`/membres [pole] [statut]` - Liste des membres

**Réunions:**

- ✅👑`/meeting_create [titre] [date] [heure] [roles] [description]` - Créer une réunion
- ✅👑`/appel [reunion]` - Faire l'appel en spécifiant le nom de la réunion
- ✅👑`/appel_id [id]` - Faire l'appel en spécifiant l'id de la réunion
- ✅👤`/meeting_stats_id [id]` - Voir les statistiques d'une réunion passée en précisant l'id
- ✅👤`/meeting_stats [reunion]` - Voir les statistiques d'une réunion passée en précisant le nom
- ✅👑`/modifier_presence [reunion] [membre] [statut]` - Modifier la présence d'un utilisateur avec le nom de la réunion
- ✅👑`/modifier_presence_id [id] [membre] [statut]` - Modifier la présence d'un utilisateur avec l'id de la réunion
- ✅👤`/meetings [pole]` - Afficher les prochaines réunions

**Rapports:**

- ✅👤`/stats [jours]` - Affiche les statisques générales du laboratoire
- ✅👤`/stats_pole [poles] [jours]` - Affiche les statistiques d'un pole
- ✅👤`/rapport [jours] [format]` - Rapport d'activité
- ✅👤`/export [type]` - Exporter les informations
