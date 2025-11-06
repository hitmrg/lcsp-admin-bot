import discord
from discord.ext import commands
from discord import app_commands
from database import Database
from .is_admin import is_admin

class Setup(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Initialise le serveur LCSP
    @app_commands.command(name="setup", description="Initialiser le serveur LCSP")
    @is_admin()
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.defer()

        guild = interaction.guild
        created = []
        errors = []

        # Créer les rôles s'ils n'existent pas
        roles_to_create = {
            "DEV": discord.Color.blue(),
            "IA": discord.Color.purple(),
            "INFRA": discord.Color.green(),
            "*": discord.Color.red(),
        }

        for role_name, color in roles_to_create.items():
            if not discord.utils.get(guild.roles, name=role_name):
                try:
                    await guild.create_role(name=role_name, color=color)
                    created.append(f"Rôle: {role_name}")
                except Exception as e:
                    errors.append(f"Rôle {role_name}: {str(e)}")

        # Structure des catégories et canaux
        categories = {
            "👑 ADMINISTRATION": ["╭🔑・logs", "╭📑・documents", "╭📢・annonces"],
        }

        # Créer les catégories et canaux
        for category_name, channels in categories.items():
            # Vérifier si la catégorie existe
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                try:
                    category = await guild.create_category(category_name)
                    created.append(f"Catégorie: {category_name}")
                except Exception as e:
                    errors.append(f"Catégorie {category_name}: {str(e)}")
                    continue

            # Créer les canaux
            for channel_name in channels:
                if not discord.utils.get(category.channels, name=channel_name):
                    try:
                        await guild.create_text_channel(channel_name, category=category)
                        created.append(f"Canal: {channel_name}")
                    except Exception as e:
                        errors.append(f"Canal {channel_name}: {str(e)}")

        # Créer l'embed de résultat
        if created or errors:
            embed = discord.Embed(
                title="⚙️ Configuration du serveur LCSP",
                color=discord.Color.green() if not errors else discord.Color.orange(),
            )

            if created:
                embed.add_field(
                    name="✅ Éléments créés",
                    value="\n".join(f"• {item}" for item in created[:10]),
                    inline=False,
                )
                if len(created) > 10:
                    embed.add_field(
                        name="",
                        value=f"... et {len(created) - 10} autres éléments",
                        inline=False,
                    )

            if errors:
                embed.add_field(
                    name="❌ Erreurs rencontrées",
                    value="\n".join(f"• {error}" for error in errors[:5]),
                    inline=False,
                )
        else:
            embed = discord.Embed(
                title="ℹ️ Configuration",
                description="Tous les éléments sont déjà configurés",
                color=discord.Color.blue(),
            )

        await interaction.followup.send(embed=embed)

# Fonction de setup du cog
async def setup(bot):
    await bot.add_cog(Setup(bot))