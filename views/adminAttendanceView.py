import discord
from discord.ext import commands
from discord import app_commands
from config import ADMIN_ROLES
import logging

logger = logging.getLogger(__name__)

# Vue Admin améliorée pour gérer l'appel complet
class AdminAttendanceView(discord.ui.View):
    def __init__(self, meeting_id, db, initiator_id, expected_members):
        super().__init__(timeout=1800)  # 30 minutes
        self.meeting_id = meeting_id
        self.db = db
        self.initiator_id = initiator_id
        self.members = expected_members
        self.page = 0
        self.members_per_page = 5
        self.attendance_status = {}
        self.validated = False

        # Initialiser avec les statuts existants
        self._load_existing_attendance()

        # Initialiser (ou mettre à jour) le select décoré défini plus bas
        first_page_members = self.get_current_page_members()
        select_options = []
        if first_page_members:
            for member in first_page_members:
                select_options.append(
                    discord.SelectOption(
                        label=self._truncate_name(member.full_name or member.username),
                        value=str(member.id),
                        description=member.role,
                        emoji="⏳",
                    )
                )

        # Rechercher un select existant (celui décoré avec @discord.ui.select)
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                # Si on a des options, on les applique, sinon on laisse le placeholder
                if select_options:
                    item.options = select_options

                # (re)définir un callback sûr qui met la selected_member_id
                async def _select_callback(select_interaction: discord.Interaction):
                    try:
                        sel = int(item.values[0])
                    except Exception:
                        await select_interaction.response.send_message(
                            "⚠️ Sélection invalide", ephemeral=True
                        )
                        return

                    self.selected_member_id = sel
                    selected_name = next(
                        (
                            m.full_name or m.username
                            for m in self.members
                            if m.id == self.selected_member_id
                        ),
                        "Membre",
                    )
                    await select_interaction.response.send_message(
                        f"✅ {selected_name} sélectionné. Choisissez maintenant son statut.",
                        ephemeral=True,
                    )

                item.callback = _select_callback
                break

    def _truncate_name(self, name: str, max_length: int = 25) -> str:
        # Tronquer le nom s'il est trop long pour le select
        if len(name) <= max_length:
            return name
        return name[: max_length - 3] + "..."

    def _load_existing_attendance(self):
        # Charger les statuts d'assiduité existants depuis la base de données
        attendances = self.db.get_meeting_attendance(self.meeting_id)
        for att, member in attendances:
            self.attendance_status[member.id] = att.status

    def get_current_page_members(self):
        """Récupérer les membres de la page actuelle"""
        start = self.page * self.members_per_page
        end = start + self.members_per_page
        return self.members[start:end]

    def get_total_pages(self):
        """Calculer le nombre total de pages"""
        return (len(self.members) - 1) // self.members_per_page + 1

    @discord.ui.select(
        placeholder="Sélectionner un membre...", min_values=1, max_values=1, row=0
    )
    async def member_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        """Sélecteur de membre pour la page actuelle"""
        # Le select sera mis à jour dynamiquement
        pass

    @discord.ui.button(label="✅ Présent", style=discord.ButtonStyle.success, row=1)
    async def mark_present(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._mark_status(interaction, "present")

    @discord.ui.button(label="❌ Absent", style=discord.ButtonStyle.danger, row=1)
    async def mark_absent(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._mark_status(interaction, "absent")

    @discord.ui.button(label="🏥 Excusé", style=discord.ButtonStyle.secondary, row=1)
    async def mark_excused(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._mark_status(interaction, "excused")

    async def _mark_status(self, interaction: discord.Interaction, status: str):
        """Marquer le statut du membre sélectionné"""
        if not hasattr(self, "selected_member_id") or not self.selected_member_id:
            await interaction.response.send_message(
                "⚠️ Veuillez d'abord sélectionner un membre dans la liste",
                ephemeral=True,
            )
            return

        # Enregistrer le statut
        self.attendance_status[self.selected_member_id] = status

        # Persister en base de données
        self.db.record_attendance(
            self.meeting_id,
            self.selected_member_id,
            status,
            modified_by=str(interaction.user.id),
        )

        # Trouver le membre pour afficher son nom
        member_name = "Membre"
        for m in self.members:
            if m.id == self.selected_member_id:
                member_name = m.full_name or m.username
                break

        await interaction.response.send_message(
            f"✅ {member_name} marqué comme {status}", ephemeral=True
        )

        # Rafraîchir l'affichage
        await self.update_display(interaction)

    @discord.ui.button(
        label="◀ Page précédente", style=discord.ButtonStyle.primary, row=2
    )
    async def prev_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page > 0:
            self.page -= 1
            await self.update_display(interaction)
        else:
            await interaction.response.send_message(
                "Vous êtes déjà à la première page", ephemeral=True
            )

    @discord.ui.button(
        label="Page suivante ▶", style=discord.ButtonStyle.primary, row=2
    )
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page < self.get_total_pages() - 1:
            self.page += 1
            await self.update_display(interaction)
        else:
            await interaction.response.send_message(
                "Vous êtes déjà à la dernière page", ephemeral=True
            )

    @discord.ui.button(
        label="🔄 Rafraîchir", style=discord.ButtonStyle.secondary, row=3
    )
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.update_display(interaction)

    @discord.ui.button(
        label="📋 Valider l'appel", style=discord.ButtonStyle.danger, row=3
    )
    async def validate_attendance(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Valider définitivement l'appel"""
        if self.validated:
            await interaction.response.send_message(
                "✅ L'appel a déjà été validé", ephemeral=True
            )
            return

        # Vérifier que l'utilisateur est autorisé
        if str(interaction.user.id) != self.initiator_id:
            member = self.db.get_member(str(interaction.user.id))
            is_admin = any(role.name in ADMIN_ROLES for role in interaction.user.roles)
            if not is_admin:
                await interaction.response.send_message(
                    "❌ Seul un administrateur peut valider l'appel", ephemeral=True
                )
                return

        # Marquer les membres non marqués comme absents
        for member in self.members:
            if member.id not in self.attendance_status:
                self.attendance_status[member.id] = "absent"
                self.db.record_attendance(
                    self.meeting_id,
                    member.id,
                    "absent",
                    modified_by=str(interaction.user.id),
                )

        # Valider l'appel en base de données
        self.db.validate_attendance(self.meeting_id, str(interaction.user.id))
        self.validated = True

        # Désactiver tous les boutons
        for item in self.children:
            item.disabled = True

        # Créer le rapport final
        present = sum(1 for s in self.attendance_status.values() if s == "present")
        absent = sum(1 for s in self.attendance_status.values() if s == "absent")
        excused = sum(1 for s in self.attendance_status.values() if s == "excused")
        total = len(self.members)
        rate = (present / total * 100) if total > 0 else 0

        embed = discord.Embed(
            title="✅ Appel validé",
            description=f"L'appel a été validé avec succès",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="✅ Présents", value=f"{present}/{total}", inline=True)
        embed.add_field(name="❌ Absents", value=f"{absent}/{total}", inline=True)
        embed.add_field(name="🏥 Excusés", value=f"{excused}/{total}", inline=True)
        embed.add_field(name="📈 Taux", value=f"{rate:.1f}%", inline=True)
        embed.set_footer(text=f"Validé par {interaction.user.display_name}")

        await interaction.response.edit_message(embed=embed, view=self)

    async def update_display(self, interaction: discord.Interaction):
        """Mettre à jour l'affichage avec la page actuelle"""
        if self.validated:
            return

        meeting = self.db.get_meeting(self.meeting_id)
        target_roles = meeting.get_target_roles()
        roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

        # Calculer les statistiques actuelles
        present = sum(1 for s in self.attendance_status.values() if s == "present")
        absent = sum(1 for s in self.attendance_status.values() if s == "absent")
        excused = sum(1 for s in self.attendance_status.values() if s == "excused")
        marked = present + absent + excused
        total = len(self.members)

        # Créer l'embed
        embed = discord.Embed(
            title=f"📢 Appel - {meeting.title}",
            description=f"**Page {self.page + 1}/{self.get_total_pages()}**\n"
            f"**Pôles:** {roles_text}\n"
            f"**Progression:** {marked}/{total} membres traités",
            color=discord.Color.blue(),
        )

        # Statistiques actuelles
        embed.add_field(
            name="📊 Statut actuel",
            value=f"✅ Présents: {present}\n❌ Absents: {absent}\n🏥 Excusés: {excused}",
            inline=True,
        )

        # Liste des membres de la page actuelle
        page_members = self.get_current_page_members()
        members_list = []

        # Mettre à jour le select avec les membres de la page
        select_options = []

        for i, member in enumerate(page_members, 1):
            status = self.attendance_status.get(member.id, "Non marqué")
            status_icon = {
                "present": "✅",
                "absent": "❌",
                "excused": "🏥",
                "Non marqué": "⏳",
            }.get(status, "⏳")

            member_display = f"{i}. {status_icon} {member.full_name or member.username} ({member.role})"
            members_list.append(member_display)

            # Ajouter l'option au select
            select_option = discord.SelectOption(
                label=f"{member.full_name or member.username}",
                value=str(member.id),
                description=f"{member.role} - {status}",
                emoji=status_icon,
            )
            select_options.append(select_option)

        embed.add_field(
            name="👥 Membres de cette page",
            value="\n".join(members_list) if members_list else "Aucun membre",
            inline=False,
        )

        # Mettre à jour le select
        if select_options:
            # Trouver et mettre à jour le select existant
            for item in self.children:
                if isinstance(item, discord.ui.Select):
                    item.options = select_options

                    # Définir le callback pour gérer la sélection
                    async def select_callback(select_interaction: discord.Interaction):
                        self.selected_member_id = int(item.values[0])
                        # Trouver le nom du membre sélectionné
                        selected_name = "Membre"
                        for m in self.members:
                            if m.id == self.selected_member_id:
                                selected_name = m.full_name or m.username
                                break
                        await select_interaction.response.send_message(
                            f"✅ {selected_name} sélectionné. Choisissez maintenant son statut.",
                            ephemeral=True,
                        )

                    item.callback = select_callback
                    break
            else:
                # Si pas de select trouvé, en créer un
                select = discord.ui.Select(
                    placeholder="Sélectionner un membre...",
                    min_values=1,
                    max_values=1,
                    options=select_options,
                    row=0,
                )

                async def select_callback(select_interaction: discord.Interaction):
                    self.selected_member_id = int(select.values[0])
                    selected_name = "Membre"
                    for m in self.members:
                        if m.id == self.selected_member_id:
                            selected_name = m.full_name or m.username
                            break
                    await select_interaction.response.send_message(
                        f"✅ {selected_name} sélectionné. Choisissez maintenant son statut.",
                        ephemeral=True,
                    )

                select.callback = select_callback
                self.add_item(select)

        # Instructions
        embed.add_field(
            name="📝 Instructions",
            value="1. Sélectionnez un membre dans la liste\n"
            "2. Cliquez sur son statut (Présent/Absent/Excusé)\n"
            "3. Naviguez entre les pages si nécessaire\n"
            "4. Validez l'appel quand terminé",
            inline=False,
        )

        embed.set_footer(text=f"Réunion du {meeting.date.strftime('%d/%m/%Y à %H:%M')}")

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            # Si l'interaction a déjà reçu une réponse, éditer le message original
            await interaction.message.edit(embed=embed, view=self)