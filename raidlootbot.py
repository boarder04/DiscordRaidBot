import asyncio
import random
import discord
from discord import app_commands, Interaction
from discord.app_commands import Range
import config

class RandomBidView(discord.ui.View):
    def __init__(self, timeout: int):
        self.user_bids = {}  # Store user bids as a dict
        super().__init__(timeout=timeout)

    async def handle_bid(self, interaction: Interaction, bid_type: str):
        user_id = interaction.user.id  # Use user ID to uniquely identify users

        if user_id in self.user_bids:
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description=f'You have already placed a bid as **{self.user_bids[user_id]}**!'
                ),
                ephemeral=True
            )
        else:
            self.user_bids[user_id] = bid_type
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.green(),
                    description=f'You have successfully bid as **{bid_type}**.'
                ),
                ephemeral=True
            )

    @discord.ui.button(label='Main', custom_id='raidMain_bid_join')
    async def join_main(self, interaction: Interaction, button: discord.ui.Button):
        await self.handle_bid(interaction, "RAID MAIN")

    @discord.ui.button(label='Approved Box', custom_id='raidBox_bid_join')
    async def join_box(self, interaction: Interaction, button: discord.ui.Button):
        await self.handle_bid(interaction, "RAID BOX")

    @discord.ui.button(label='Alt', custom_id='alt_bid_join')
    async def join_alt(self, interaction: Interaction, button: discord.ui.Button):
        await self.handle_bid(interaction, "ALT")

    @discord.ui.button(label='Leave', custom_id='bid_leave')
    async def leave(self, interaction: Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id not in self.user_bids:
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.red(), 
                    description='You have not joined the bid!'
                ),
                ephemeral=True
            )
        else:
            bid_type = self.user_bids.pop(user_id)
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.green(), 
                    description=f'You have left the bid as **{bid_type}**.'
                ),
                ephemeral=True
            )


class PlatBidView(discord.ui.View):
    def __init__(self, timeout: int):
        super().__init__(timeout=timeout)
        self.bids = {}

    @discord.ui.button(label='Bid', style=discord.ButtonStyle.green, custom_id='bid_button')
    async def bid_button(self, interaction: Interaction, button: discord.ui.Button):
        modal = PlatBidModal(self.bids)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Leave Bid', style=discord.ButtonStyle.red, custom_id='leave_bid_button')
    async def leave_bid_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.display_name in self.bids:
            del self.bids[interaction.user.display_name]
            await interaction.response.send_message("You have left the bid.", ephemeral=True)
        else:
            await interaction.response.send_message("You did not place a bid.", ephemeral=True)

    def get_sorted_bids(self):
        return sorted(self.bids.items(), key=lambda x: x[1], reverse=True)

class PlatBidModal(discord.ui.Modal):
    def __init__(self, bids):
        super().__init__(title=f"Place Your Bid (Minimum Bid: {CustomBot.min_bid:,})")
        self.bids = bids

    bid_amount = discord.ui.TextInput(label="Bid Amount", placeholder="Enter your bid amount here")

    async def on_submit(self, interaction: Interaction):
        bid_amount_str = self.bid_amount.value.replace(",", "")
        try:
            bid_amount = int(bid_amount_str)
        except ValueError:
            await interaction.response.send_message("Please enter a valid number for the bid amount.", ephemeral=True)
            return

        if bid_amount < CustomBot.min_bid:
            await interaction.response.send_message(f"Your bid must be at least {CustomBot.min_bid}.", ephemeral=True)
            return


        self.bids[interaction.user.display_name] = bid_amount
        await interaction.response.send_message(f"Your bid of {bid_amount} has been placed.", ephemeral=True)

class CustomBot(discord.Client):
    min_bid = 1  # Class attribute for minimum bid

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents, help_command=None)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.clear_commands(guild=None)
        self.tree.add_command(start_random)
        self.tree.add_command(start_bids)
        self.tree.add_command(set_min_bid)
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user}')

bot = CustomBot()

@bot.tree.command(name='random')
@app_commands.guild_only()
@app_commands.describe(item='The name of the item', classes='Who can roll on the item', time='The time in seconds until the end of the bid')
async def start_random(interaction: Interaction, item: str, classes: str, time: Range[int, 1, 600]):
    """Starts a bid for an item."""

    view = RandomBidView(time)
    embed = discord.Embed(
        color=discord.Color.blue(),
        description=f'Now rolling: **{item}**!\n\nThe following may bid:\n**{classes}**'
    )

    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(time)
    view.stop()

    bid_entries = [f'{interaction.guild.get_member(user_id).display_name} ({bid_type})' for user_id, bid_type in view.user_bids.items() if interaction.guild.get_member(user_id)]
    random.shuffle(bid_entries)
    winners_text = '\n'.join(bid_entries)
    embed.description += f'\n\n**Results**:\n{winners_text if winners_text else "No users joined!"}'

    # Disable all buttons after the bidding period is over
    for item in view.children:
        item.disabled = True

    await interaction.edit_original_response(embed=embed, view=view)

@bot.tree.command(name='bid')
@app_commands.guild_only()
@app_commands.describe(item='The name of the item', classes='Who can bid on the item', time='The time in seconds until the end of the bid \n(There are 86400 seconds in a day)')
async def start_bids(interaction: Interaction, item: str, classes: str, time: Range[int, 1, 600]):
    view = PlatBidView(time)
    embed = discord.Embed(
        color=discord.Color.blue(),
        description=f'Now bidding: **{item}**!\n\nThe following may bid:\n**{classes}**'
    )

    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(time)
    view.stop()

    sorted_bids = view.get_sorted_bids()

    # Determine the payment amount
    if len(sorted_bids) >= 2:
        payment_amount = sorted_bids[1][1] + 1  # Second place bid + 1
    elif len(sorted_bids) == 1:
        payment_amount = bot.min_bid + 1  # Minimum bid + 1 if only one bid
    else:
        payment_amount = None  # No bids were placed

    winners_text = '\n'.join(f'{user} bid {amount:,}' for user, amount in sorted_bids)
    payment_text = f"Payment amount: {payment_amount:,}" if payment_amount is not None else "No bids were placed!"

    embed.description += f'\n\n**Results**:\n{winners_text}\n\n{payment_text}'

    for item in view.children:
        item.disabled = True

    await interaction.edit_original_response(embed=embed, view=view)

@bot.tree.command(name='minbid')
@app_commands.describe(min_bid='The minimum bid amount')
async def set_min_bid(interaction: Interaction, min_bid: int):
    """Sets the minimum bid amount."""
    CustomBot.min_bid = max(1, min_bid)
    await interaction.response.send_message(f"Minimum bid set to {CustomBot.min_bid}.", ephemeral=True)

bot.run(config.TOKEN)
