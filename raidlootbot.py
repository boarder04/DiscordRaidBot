import asyncio
import random

import discord
from  discord import app_commands, Interaction
from  discord.app_commands import Range

import config


class BidView(discord.ui.View):
    def __init__(self, timeout: int):
        self.users: list[discord.Member] = []
        super().__init__(timeout=timeout)

    @discord.ui.button(label='Join', custom_id='bid_join')
    async def join(self, interaction: Interaction, button: discord.ui.Button):
        """Joins the bid."""

        if interaction.user in self.users:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description='You already joined this bid!'
                ),
                ephemeral=True
            )

        #self.users.append(interaction.user)
        self.users.append(interaction.user + " ALT")

        await interaction.response.send_message(
            embed=discord.Embed(
                color=discord.Color.green(),
                description='Successfully joined the bid!'
            ),
            ephemeral=True
        )

    @discord.ui.button(label='Leave', custom_id='bid_leave')
    async def leave(self, interaction: Interaction, button: discord.ui.Button):
        """Leaves the bid."""

        if interaction.user not in self.users:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description='You did not join this bid!'
                ),
                ephemeral=True
            )

        self.users.remove(interaction.user)

        await interaction.response.send_message(
            embed=discord.Embed(
                color=discord.Color.green(),
                description='Successfully left the bid!'
            ),
            ephemeral=True
        )


class CustomBot(discord.Client):
    tree: app_commands

    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents, help_command=None)

        self.tree = app_commands.CommandTree(self)


    async def setup_hook(self):
        """Syncs the slash commands."""

        await self.tree.sync()


bot = CustomBot()


@bot.event
async def on_ready():
    print(f'-------------------- Bot is ready! --------------------')
    print(f'Logged in as {bot.user}'.center(55))
    print(f'-------------------------------------------------------')


@bot.tree.command(name='startbids')
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.describe(item='The item to start the bid for', time='The time in seconds until the end of the bid')
async def start_bids(interaction: Interaction, item: str, time: Range[int, 1, 1000000]):
    """Starts a bid for an item."""

    view = BidView(time)
    embed = discord.Embed(
        color=discord.Color.blue(),
        description=f'Now rolling: **{item}**!'
    )

    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(time)
    view.stop()

    random.shuffle(view.users)
    winners_text = '\n'.join(user.mention for user in view.users)
    embed.description += f'\n\n**Results**:\n{winners_text or "No users joined!"}'

    view.join.disabled = True
    view.leave.disabled = True

    await interaction.edit_original_response(embed=embed, view=view)


bot.run(config.TOKEN)