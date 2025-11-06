import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

# Vue pour la pagination de la liste des membres
class MemberListView(discord.ui.View):

    def __init__(self, embeds):
        super().__init__(timeout=180)  # 3 minutes
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()

    # Mettre à jour l'état des boutons
    def update_buttons(self):
        self.previous.disabled = self.current_page == 0
        self.next.disabled = self.current_page >= len(self.embeds) - 1

    @discord.ui.button(
        label="◀ Précédent", style=discord.ButtonStyle.primary, disabled=True
    )
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(
                embed=self.embeds[self.current_page], view=self
            )

    @discord.ui.button(label="Suivant ▶", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(
                embed=self.embeds[self.current_page], view=self
            )

    @discord.ui.button(label="🏠", style=discord.ButtonStyle.secondary)
    async def home(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[0], view=self)